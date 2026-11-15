import pandas as pd
import config


def resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample(rule).agg(agg).dropna()


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def swings(df, mult=None):
    mult = mult or config.SWING_ATR_MULT
    hi, lo = df["high"].values, df["low"].values
    a = atr(df).values
    t = df.index
    out, d = [], 0
    hi_i = lo_i = 0
    hi_p, lo_p = hi[0], lo[0]
    for i in range(1, len(df)):
        th = a[i] * mult
        if d == 0:
            if hi_p - lo[i] >= th and hi_i < i:
                out.append((hi_i, hi_p, "H")); d = -1; lo_i, lo_p = i, lo[i]
            elif hi[i] - lo_p >= th and lo_i < i:
                out.append((lo_i, lo_p, "L")); d = 1; hi_i, hi_p = i, hi[i]
            else:
                if hi[i] > hi_p: hi_i, hi_p = i, hi[i]
                if lo[i] < lo_p: lo_i, lo_p = i, lo[i]
        elif d == 1:
            if hi[i] > hi_p:
                hi_i, hi_p = i, hi[i]
            elif hi_p - lo[i] >= th:
                out.append((hi_i, hi_p, "H")); d = -1; lo_i, lo_p = i, lo[i]
        else:
            if lo[i] < lo_p:
                lo_i, lo_p = i, lo[i]
            elif hi[i] - lo_p >= th:
                out.append((lo_i, lo_p, "L")); d = 1; hi_i, hi_p = i, hi[i]
    pending = None
    if d == 1: pending = (hi_i, hi_p, "H")
    if d == -1: pending = (lo_i, lo_p, "L")
    res = [{"i": i, "t": t[i], "p": float(p), "k": k, "pending": False}
           for i, p, k in out]
    if pending:
        i, p, k = pending
        res.append({"i": i, "t": t[i], "p": float(p), "k": k, "pending": True})
    return res

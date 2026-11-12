import pandas as pd


def resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample(rule).agg(agg).dropna()


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def swings(df, mult=2.0):
    """ATR zigzag. Returns alternating pivots; the last one is still forming."""
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
    res = [{"i": i, "t": t[i], "p": float(p), "k": k, "pending": False} for i, p, k in out]
    if pending:
        i, p, k = pending
        res.append({"i": i, "t": t[i], "p": float(p), "k": k, "pending": True})
    return res


def _near(x, target, tol):
    return abs(x - target) <= tol


def check_impulse(p):
    s = 1 if p[1] > p[0] else -1
    w1 = (p[1]-p[0])*s; w2 = (p[1]-p[2])*s; w3 = (p[3]-p[2])*s
    w4 = (p[3]-p[4])*s; w5 = (p[5]-p[4])*s
    if min(w1, w2, w3, w4, w5) <= 0 or w2 >= w1:
        return None                                   # rule 1
    if w3 < w1 and w3 < w5:
        return None                                   # rule 2
    kind, score, notes = "impulse complete", 50, []
    if (p[4]-p[1])*s <= 0:                            # rule 3 (overlap)
        if not (w3 < w1 and w5 < w3):
            return None
        kind, score = "ending diagonal complete", 40
        notes.append("wave 4 overlaps wave 1 (diagonal)")
    r2, e3, r4 = w2/w1, w3/w1, w4/w3
    if 0.5 <= r2 <= 0.786: score += 15
    elif 0.382 <= r2 < 0.5: score += 8
    if _near(e3, 1.618, 0.2): score += 15
    elif 1.0 <= e3 <= 2.618: score += 8
    if w3 > w1 and w3 > w5: score += 5
    if 0.236 <= r4 <= 0.382: score += 10
    elif 0.382 < r4 <= 0.5: score += 5
    if (r2 > 0.5) != (r4 > 0.5): score += 5           # alternation
    if _near(w5/w1, 1.0, 0.2): score += 5
    if (p[5]-p[3])*s <= 0:
        kind += " (truncated 5th)"; score -= 5
    notes.append(f"w2 {r2:.0%} of w1, w3 {e3:.2f}x w1, w4 {r4:.0%} of w3")
    return dict(kind=kind, dir=s, score=score, notes=notes, pivots=list(p))


def check_abc(p):
    s = 1 if p[1] > p[0] else -1
    a = (p[1]-p[0])*s; b = (p[1]-p[2])*s; c = (p[3]-p[2])*s
    if min(a, b, c) <= 0:
        return None
    rb, rc, score, notes = b/a, c/a, 50, []
    if rb < 0.9:
        if rb < 0.236 or rb > 0.786 or (p[3]-p[1])*s <= 0:
            return None
        kind = "zigzag A-B-C complete"
        if 0.382 <= rb <= 0.786: score += 15
        if 0.618 <= rc <= 1.618: score += 15
        if _near(rc, 1.0, 0.1) or _near(rc, 1.618, 0.1): score += 5
    else:
        if rb > 1.382 or not (0.9 <= rc <= 1.7):
            return None
        kind = "flat A-B-C complete" if rb <= 1.0 else "expanded flat A-B-C complete"
        score += 15
        if _near(rc, 1.0, 0.1) or _near(rc, 1.618, 0.1): score += 10
    notes.append(f"B {rb:.0%} of A, C {rc:.2f}x A")
    return dict(kind=kind, dir=s, score=score, notes=notes, pivots=list(p))


def check_w2(p):
    s = 1 if p[1] > p[0] else -1
    w1 = (p[1]-p[0])*s; w2 = (p[1]-p[2])*s
    if w1 <= 0 or w2 <= 0 or w2 >= w1:
        return None
    r, score = w2/w1, 50
    if 0.5 <= r <= 0.786: score += 15
    elif 0.382 <= r < 0.5 or 0.786 < r <= 0.9: score += 5
    return dict(kind="wave 3 in progress", dir=s, score=score,
                notes=[f"wave 2 at {r:.0%} of wave 1"], pivots=list(p))


def check_w4(p):
    s = 1 if p[1] > p[0] else -1
    w1 = (p[1]-p[0])*s; w2 = (p[1]-p[2])*s; w3 = (p[3]-p[2])*s; w4 = (p[3]-p[4])*s
    if min(w1, w2, w3, w4) <= 0 or w2 >= w1 or w3 < w1:
        return None
    if (p[4]-p[1])*s <= 0:
        return None                                   # overlap
    r2, e3, r4, score = w2/w1, w3/w1, w4/w3, 50
    if 0.5 <= r2 <= 0.786: score += 10
    if _near(e3, 1.618, 0.2): score += 15
    elif e3 >= 1.0: score += 8
    if 0.236 <= r4 <= 0.382: score += 15
    elif 0.382 < r4 <= 0.5: score += 8
    elif r4 > 0.618: return None
    if (r2 > 0.5) != (r4 > 0.5): score += 5
    return dict(kind="wave 5 in progress", dir=s, score=score,
                notes=[f"w3 {e3:.2f}x w1, w4 at {r4:.0%} of w3"], pivots=list(p))


def find_counts(sw, depth=14):
    pts = sw[-depth:]
    n, res = len(pts), []
    for L, fn in ((6, check_impulse), (4, check_abc), (5, check_w4), (3, check_w2)):
        for st in range(max(0, n-L-2), n-L+1):
            seg = pts[st:st+L]
            c = fn([x["p"] for x in seg])
            if not c:
                continue
            back = n - (st+L)
            if c["kind"].endswith("in progress") and back:
                continue
            c["score"] -= back * 8
            c["start"], c["end"] = seg[0]["t"], seg[-1]["t"]
            res.append(c)
    return sorted(res, key=lambda c: -c["score"])

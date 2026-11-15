def fib_levels(c):
    """Targets / zones that belong to the current count, highest price first."""
    p, s, k = c["pivots"], c["dir"], c["kind"]
    out = []
    if k == "wave 3 in progress":
        w1 = abs(p[1] - p[0])
        for e in (1.0, 1.618, 2.618):
            out.append((f"Wave 3 = {e}x wave 1", p[2] + s * w1 * e))
    elif k == "wave 5 in progress":
        w1, net = abs(p[1] - p[0]), abs(p[3] - p[0])
        out += [("Wave 5 = 0.618x wave 1", p[4] + s * 0.618 * w1),
                ("Wave 5 = 1.0x wave 1", p[4] + s * w1),
                ("Wave 5 = 0.618x waves 1-3", p[4] + s * 0.618 * net)]
    else:
        L = abs(p[-1] - p[0])
        impulse = k.startswith(("impulse", "ending diagonal"))
        for r in ((0.382, 0.5, 0.618) if impulse else (0.618, 1.0, 1.618)):
            name = f"{r} retrace of whole move" if impulse else f"{r}x of the correction"
            out.append((name, p[-1] - s * r * L))
    return sorted(out, key=lambda x: -x[1])


def leg_retracements(sw):
    """Pullback levels of the current leg (last two swings)."""
    if len(sw) < 2:
        return []
    a, b = sw[-2]["p"], sw[-1]["p"]
    return [(f"{r} pullback", b - (b - a) * r) for r in (0.382, 0.5, 0.618, 0.786)]


def key_levels(sw, price):
    conf = [x["p"] for x in sw[:-1]][-12:]
    res = sorted(p for p in conf if p > price)[:2]
    sup = sorted((p for p in conf if p < price), reverse=True)[:2]
    lo = int(price // 50) * 50
    return {"res": res, "sup": sup, "round": [lo, lo + 50]}


def candle_pattern(df):
    """Pattern on the last CLOSED candle (the latest candle may still be forming)."""
    if len(df) < 4:
        return None
    a, b = df.iloc[-3], df.iloc[-2]
    ao, ac = a["open"], a["close"]
    bo, bc, bh, bl = b["open"], b["close"], b["high"], b["low"]
    rng, body = bh - bl, abs(bc - bo)
    if rng <= 0:
        return None
    up_w, lo_w = bh - max(bo, bc), min(bo, bc) - bl
    if bc > bo and ac < ao and bc >= ao and bo <= ac:
        return "bullish engulfing"
    if bc < bo and ac > ao and bc <= ao and bo >= ac:
        return "bearish engulfing"
    if lo_w > 2 * body and lo_w > 0.6 * rng:
        return "bullish pin bar (long lower wick)"
    if up_w > 2 * body and up_w > 0.6 * rng:
        return "bearish pin bar (long upper wick)"
    return None

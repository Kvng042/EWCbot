def _near(x, target, tol):
    return abs(x - target) <= tol


def check_impulse(p):
    s = 1 if p[1] > p[0] else -1
    w1 = (p[1]-p[0])*s; w2 = (p[1]-p[2])*s; w3 = (p[3]-p[2])*s
    w4 = (p[3]-p[4])*s; w5 = (p[5]-p[4])*s
    if min(w1, w2, w3, w4, w5) <= 0 or w2 >= w1:
        return None
    if w3 < w1 and w3 < w5:
        return None
    kind, score, notes = "impulse complete", 50, []
    if (p[4]-p[1])*s <= 0:
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
    if (r2 > 0.5) != (r4 > 0.5): score += 5
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
    rb, rc, score = b/a, c/a, 50
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
    return dict(kind=kind, dir=s, score=score,
                notes=[f"B {rb:.0%} of A, C {rc:.2f}x A"], pivots=list(p))


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
        return None
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


def check_triangle(p):
    s = 1 if p[1] > p[0] else -1
    l = [abs(p[i+1] - p[i]) for i in range(5)]
    good = 0
    for i in range(4):
        r = l[i+1] / l[i]
        if not (0.382 <= r <= 0.95):
            return None
        if 0.5 <= r <= 0.786: good += 1
    return dict(kind="triangle complete", dir=s, score=55 + good * 4,
                notes=["5 contracting legs: " + ", ".join(f"{x:.1f}" for x in l)],
                pivots=list(p))


def check_wxy(p):
    w, y = check_abc(p[0:4]), check_abc(p[4:8])
    if not w or not y or w["dir"] != y["dir"]:
        return None
    s = w["dir"]
    wl, x, yl = (p[3]-p[0])*s, (p[3]-p[4])*s, (p[7]-p[4])*s
    if wl <= 0 or x <= 0:
        return None
    rx = x / wl
    if not (0.382 <= rx <= 1.0) or yl < 0.618 * wl:
        return None
    score = int((w["score"] + y["score"]) / 2) - 5
    return dict(kind="W-X-Y complete", dir=s, score=score,
                notes=[f"X {rx:.0%} of W; W is {w['kind'].split(' A')[0]}, "
                       f"Y is {y['kind'].split(' A')[0]}"],
                pivots=list(p))


SPECS = [(6, check_impulse), (6, check_triangle), (4, check_abc),
         (8, check_wxy), (5, check_w4), (3, check_w2)]


def find_counts(sw, depth=16):
    pts = sw[-depth:]
    n, res = len(pts), []
    for L, fn in SPECS:
        for back in range(0, 4):
            st = n - L - back
            if st < 0:
                break
            seg = pts[st:st+L]
            c = fn([x["p"] for x in seg])
            if not c:
                continue
            live = c["kind"].endswith("in progress")
            # FIX: live counts may use the forming leg (back 0) or stop one leg
            # before it (back 1); finished patterns must exclude the forming leg.
            if live and back > 1:
                continue
            if not live and back == 0:
                continue
            c["score"] -= max(0, back - 1) * 8
            c["start"], c["end"] = str(seg[0]["t"]), str(seg[-1]["t"])
            c["times"] = [str(x["t"]) for x in seg]
            res.append(c)
    return sorted(res, key=lambda c: -c["score"])

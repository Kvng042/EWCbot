import config
from data import tf_data
from swings import swings
from patterns import find_counts


def sig(c):
    return f"{c['kind']}|{c['start']}"


def bias(c):
    """Direction the market is expected to move next, given this count."""
    return c["dir"] if c["kind"].endswith("in progress") else -c["dir"]


def clear(cs):
    """The best count, only if it is strong and clearly ahead of the rest."""
    if not cs or cs[0]["score"] < config.MIN_SCORE:
        return None
    if len(cs) > 1 and cs[0]["score"] - cs[1]["score"] < config.MIN_GAP:
        return None
    return cs[0]


def inval(c):
    """(level, side): the count is invalid when (price - level) * side < 0."""
    p, s, k = c["pivots"], c["dir"], c["kind"]
    if k == "wave 3 in progress": return p[0], s
    if k == "wave 5 in progress": return p[1], s
    return p[-1], -s


def broken(level, side, price):
    return (price - level) * side < 0


def where(side):
    return "below" if side > 0 else "above"


_memo = {}


def analyze(df5):
    """All counts for every timeframe. Cached until a new candle arrives."""
    key = (str(df5.index[-1]), len(df5))
    if _memo.get("key") != key:
        _memo["key"] = key
        _memo["val"] = {n: find_counts(swings(tf_data(n, df5)))
                        for n in config.RESAMPLE}
    return _memo["val"]


def confidence(cs):
    """0-95%: how well the best count fits the rules and leads its rivals."""
    if not cs:
        return 0
    rival = cs[1]["score"] if len(cs) > 1 else 40
    gap = max(0, cs[0]["score"] - rival)
    return int(max(5, min(95, cs[0]["score"] - 10 + min(15, gap))))


def alignment(best):
    """best: {tf: clear count or None}. Returns (direction or None, text)."""
    dirs = {tf: bias(c) for tf, c in best.items() if c and tf != "5m"}
    parts = ", ".join(f"{tf} {'up' if d > 0 else 'down'}" for tf, d in dirs.items())
    if (not any(t in dirs for t in ("4h", "1h")) or len(dirs) < 2
            or len(set(dirs.values())) > 1):
        return None, "No aligned direction. " + (parts or "No clear counts.")
    d = next(iter(dirs.values()))
    return d, ("BUY" if d > 0 else "SELL") + " bias: " + parts

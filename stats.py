"""Trade results: win rate and R-multiples, overall and per setup."""
import config

NAMES = {"W3": "Wave 3 entry", "W5": "Wave 5 entry", "CORR": "Correction-end entry"}


def _s(st):
    return st.setdefault("stats", {"wins": 0, "losses": 0, "r": 0.0, "by": {}})


def record(st, setup, R, paper):
    """Add one closed trade. R = profit in multiples of the risk taken."""
    s = _s(st)
    b = s["by"].setdefault(setup, {"n": 0, "wins": 0, "r": 0.0})
    b["n"] += 1
    b["wins"] += int(R > 0)
    b["r"] = round(b["r"] + float(R), 3)
    if not paper:
        s["wins"] += int(R > 0)
        s["losses"] += int(R <= 0)
        s["r"] = round(s["r"] + float(R), 3)


def setup_mode(st, setup):
    """'unproven' (under MIN_PROVEN results), 'live', or 'paper' (losing, silent)."""
    b = (st.get("stats") or {}).get("by", {}).get(setup)
    if not b or b["n"] < config.MIN_PROVEN:
        return "unproven"
    return "live" if b["r"] >= 0 else "paper"


def record_line(st, setup):
    b = (st.get("stats") or {}).get("by", {}).get(setup)
    n = b["n"] if b else 0
    if n < config.MIN_PROVEN:
        return f"unproven ({n}/{config.MIN_PROVEN} results so far)"
    return f"{n} trades, {100 * b['wins'] // n}% won, {b['r']:+.1f}R"


def text(st):
    s = st.get("stats") or {}
    n = s.get("wins", 0) + s.get("losses", 0)
    if n == 0:
        head = "No closed trade signals yet."
    else:
        head = (f"Signals closed: {n}\nWin rate: {100 * s['wins'] // n}%\n"
                f"Total: {s['r']:+.1f}R  (average {s['r'] / n:+.2f}R per trade)")
    lines = [head, "", "BY SETUP"]
    for code, name in NAMES.items():
        mode = setup_mode(st, code)
        tag = {"unproven": "", "live": "", "paper": "  [PAUSED: losing, tracked silently]"}[mode]
        lines.append(f"  {name}: {record_line(st, code)}{tag}")
    return "\n".join(lines)

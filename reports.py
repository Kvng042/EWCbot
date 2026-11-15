import config
import state
import levels
import chart
from data import get_5m, get_hourly, tf_data, source
from swings import swings
from analysis import (analyze, clear, inval, where, alignment, bias, confidence)


def counts_text():
    """Short summary of all timeframes."""
    df = get_5m()
    lines = [f"XAUUSD {df['close'].iloc[-1]:.2f} ({df.index[-1]:%d %b %H:%M} UTC)"]
    best = {}
    for name, cs in analyze(df).items():
        if not cs:
            lines.append(f"\n{name}: no count found")
            continue
        c, ok = cs[0], clear(cs)
        best[name] = ok
        lvl, side = inval(c)
        lines.append(f"\n{name} [{'CLEAR' if ok else 'unclear'}]: {c['kind']}, "
                     f"confidence {confidence(cs)}%\n"
                     f"  invalid if price goes {where(side)} {lvl:.2f}")
    lines.append("\n" + alignment(best)[1])
    return "\n".join(lines)


def selftest_text():
    df = get_5m()
    lines = [f"Data OK ({source['name']}): {len(df)} 5min candles",
             f"From {df.index[0]:%d %b %H:%M} to {df.index[-1]:%d %b %H:%M} UTC",
             f"Last price {df['close'].iloc[-1]:.2f}"]
    for name in config.RESAMPLE:
        d = tf_data(name, df)
        lines.append(f"{name}: {len(d)} candles, {len(swings(d))} swings")
    h = get_hourly()
    lines.append("Hourly history: " +
                 (f"{len(h)} candles (Yahoo)" if h is not None else "not available"))
    return "\n".join(lines)


def _stats_line():
    s = state.load().get("stats") or {}
    w, l = s.get("wins", 0), s.get("losses", 0)
    if w + l < 5:
        return "building (needs 5+ closed trade signals)"
    return f"{w}/{w + l} signals won ({100 * w // (w + l)}%)"


def _prices(items):
    return [f"  {name}: {p:.2f}" for name, p in items]


def analysis(tf):
    """Full analysis for one timeframe. Returns (text, chart_png_or_None, caption)."""
    df5 = get_5m()
    price = float(df5["close"].iloc[-1])
    an = analyze(df5)
    cs = an[tf]
    d = tf_data(tf, df5)
    head = f"XAUUSD {tf.upper()} | {price:.2f} | {df5.index[-1]:%d %b %H:%M} UTC"
    if not cs:
        return head + "\n\nNo valid Elliott wave count on this timeframe right now.", None, head

    sw = swings(d)
    c, ok, conf = cs[0], clear(cs), confidence(cs)
    lvl, side = inval(c)
    fibs, pulls = levels.fib_levels(c), levels.leg_retracements(sw)
    keys = levels.key_levels(sw, price)
    candle = levels.candle_pattern(d)
    best = {n: clear(an[n]) for n in config.WATCH_TFS}

    L = [head, "",
         f"COUNT: {c['kind']}",
         f"Status: {'CLEAR' if ok else 'UNCLEAR, a rival count is close'}",
         f"Next expected move: {'UP' if bias(c) > 0 else 'DOWN'}",
         f"Confidence: {conf}% (rule fit, not a win rate)",
         f"Track record: {_stats_line()}",
         "Rules: " + "; ".join(c["notes"]), "",
         f"INVALIDATION: count fails if price goes {where(side)} {lvl:.2f} "
         f"({abs(price - lvl):.1f} away)", "",
         "FIB TARGETS / ZONES"] + _prices(fibs) + \
        ["", "PULLBACK LEVELS (current leg)"] + _prices(pulls) + \
        ["", "KEY LEVELS",
         "  Resistance: " + (", ".join(f"{x:.2f}" for x in keys["res"]) or "none nearby"),
         "  Support: " + (", ".join(f"{x:.2f}" for x in keys["sup"]) or "none nearby"),
         "  Round numbers: " + ", ".join(str(x) for x in keys["round"]),
         "", "PATTERN CHECK"]
    for i, x in enumerate(cs[:3], 1):
        L.append(f"  {i}) {x['kind']} (score {x['score']})")
    L += ["  Last closed candle: " + (candle or "no notable pattern"),
          "", "MULTI-TIMEFRAME", "  " + alignment(best)[1]]

    png = None
    try:
        png = chart.draw(d, c, f"XAUUSD {tf.upper()}: {c['kind']} ({conf}%)",
                         lvl, fibs, keys)
    except Exception as e:
        L.append(f"\n(Chart unavailable: {e})")
    return "\n".join(L), png, f"{head}\n{c['kind']} | confidence {conf}%"

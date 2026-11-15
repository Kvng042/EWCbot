"""Trade scanner: finds setups on the 15m and 5m charts in the direction of the
higher-timeframe counts, sends anticipations and signals, and manages open trades."""
import time
import pandas as pd
import config
import tg
import levels
import filters
import stats
import chart
from data import tf_data
from swings import atr
from analysis import get_swings, clear, bias, inval, where

CORRECTIONS = ("zigzag A-B-C complete", "flat A-B-C complete",
               "expanded flat A-B-C complete", "triangle complete", "W-X-Y complete")


def _side(D):
    return "BUY" if D > 0 else "SELL"


# ---------- direction and setups ----------
def trade_bias(an):
    """Direction from the clear 4h / 1h / 15m counts. None if they disagree or are unclear."""
    best = {n: clear(an[n]) for n in ("4h", "1h", "15m")}
    dirs = {n: bias(c) for n, c in best.items() if c}
    if not any(n in dirs for n in ("4h", "1h")) or len(set(dirs.values())) > 1:
        return None, "", best
    D = next(iter(dirs.values()))
    txt = ", ".join(f"{n} {'up' if d > 0 else 'down'}" for n, d in dirs.items())
    return D, txt, best


def entry_count(cs):
    """Entry timeframes may be slightly less clear-cut than the higher ones."""
    if not cs or cs[0]["score"] < config.MIN_SCORE:
        return None
    if len(cs) > 1 and cs[0]["score"] - cs[1]["score"] < config.ENTRY_MIN_GAP:
        return None
    return cs[0]


def make_plan(tf, c, D, a, sw):
    """Turn a count into a trade plan (trigger, stop, targets) or None."""
    p, s, k = c["pivots"], c["dir"], c["kind"]
    buf = 0.5 * a
    base = dict(tf=tf, dir=D, c=c)
    if k == "wave 3 in progress" and s == D:
        w1 = abs(p[1] - p[0])
        return dict(base, code="W3", trigger=p[1], stop=p[2] - D * buf, zone=p[2],
                    tp1=p[2] + D * 1.618 * w1, tp2=p[2] + D * 2.618 * w1,
                    plan_b=f"if price goes {where(D)} {p[0]:.2f}, wave 2 has failed. "
                           f"Exit and wait for a recount.")
    if k == "wave 5 in progress" and s == D:
        w1, net = abs(p[1] - p[0]), abs(p[3] - p[0])
        near, far = sorted((w1, 0.618 * net))
        return dict(base, code="W5", trigger=p[3], stop=p[4] - D * buf, zone=p[4],
                    tp1=p[4] + D * near, tp2=p[4] + D * far,
                    plan_b=f"if price goes {where(D)} {p[1]:.2f}, wave 4 overlaps wave 1 "
                           f"(not a clean impulse). Exit.")
    if (k in CORRECTIONS and -s == D and len(sw) >= 2
            and c["times"][-1] == str(sw[-2]["t"])):
        trig = sw[-1]["p"]
        if (trig - p[-1]) * D <= 0:
            return None
        L = abs(p[-1] - p[0])
        return dict(base, code="CORR", trigger=trig, stop=p[-1] - D * buf, zone=p[-1],
                    tp1=p[-1] + D * 0.618 * L, tp2=p[-1] + D * 1.0 * L,
                    plan_b=f"if price goes {where(D)} {p[-1]:.2f}, the correction is still "
                           f"extending (possibly W-X-Y). Exit.")
    return None


def other_levels(an, sws, exclude_tf):
    """Fib and swing levels from the other timeframes, for the confluence check."""
    out = []
    for n in config.WATCH_TFS:
        if n == exclude_tf or n not in sws:
            continue
        if an[n]:
            out += [p for _, p in levels.fib_levels(an[n][0])]
        out += [p for _, p in levels.leg_retracements(sws[n])]
        out += [x["p"] for x in sws[n][:-1][-6:]]
    return out


def quality(pl, d, sw, a, others):
    """Returns (points, notes, blocked_reason or None)."""
    D, c, notes, pts = pl["dir"], pl["c"], [], 0
    n = filters.confluence(pl["zone"], others, 0.6 * a)
    if n >= 2:
        pts += 1
        notes.append(f"Fib/level confluence: {n} levels near {pl['zone']:.2f}")
    if pl["code"] == "W5" and filters.wave4_channel_ok(c, 0.6 * a):
        pts += 1
        notes.append("Wave 4 ended on the trendline through waves 0-2")
    cp = levels.candle_pattern(d)
    if cp and (("bullish" in cp) == (D > 0)):
        pts += 1
        notes.append(f"Candle: {cp}")
    if filters.momentum_agrees(d, D):
        pts += 1
        notes.append("RSI momentum agrees")
    div = filters.divergence(d, sw)
    if div:
        against = (div == "bearish" and D > 0) or (div == "bullish" and D < 0)
        if against:
            if pl["code"] == "W5":
                return pts, notes, f"RSI {div} divergence: momentum fading on a wave 5 entry"
            pts -= 1
            notes.append(f"Warning: RSI {div} divergence")
        else:
            pts += 1
            notes.append(f"RSI {div} divergence supports the trade")
    return pts, notes, None


def _eval(pl, entry):
    """Risk and reward numbers for an entry price, or (None, reason)."""
    D = pl["dir"]
    risk = (entry - pl["stop"]) * D
    if risk <= 0:
        return None, "the stop level was already passed"
    if not (config.MIN_STOP <= risk <= config.MAX_STOP):
        return None, f"stop distance {risk:.1f} is outside the allowed range"
    if (pl["tp1"] - entry) * D <= 0:
        return None, "TP1 was already passed"
    rr1 = (pl["tp1"] - entry) * D / risk
    rr2 = (pl["tp2"] - entry) * D / risk
    if rr1 < config.MIN_RR:
        return None, f"reward-to-risk {rr1:.2f} is below {config.MIN_RR}"
    return dict(risk=risk, rr1=rr1, rr2=rr2), ""


# ---------- messages ----------
def _notes(notes):
    return "\n".join("  " + n for n in notes) or "  none"


def _ant_text(pl, ev, price, bias_txt, notes, pts, st):
    D = pl["dir"]
    return (f"👀 ANTICIPATION: {_side(D)} XAUUSD | {pl['tf']} {stats.NAMES[pl['code']]}\n"
            f"Direction bias: {bias_txt}\n"
            f"Watching: a {pl['tf']} candle close {'above' if D > 0 else 'below'} "
            f"{pl['trigger']:.2f} (price now {price:.2f})\n"
            f"If it triggers: stop {pl['stop']:.2f}, TP1 {pl['tp1']:.2f}, "
            f"TP2 {pl['tp2']:.2f} (RR {ev['rr1']:.1f})\n"
            f"Quality so far: {pts} point(s)\n{_notes(notes)}\n"
            f"Cancel if {pl['plan_b']}\n"
            f"Setup record: {stats.record_line(st, pl['code'])}")


def _signal_text(pl, ev, price, bias_txt, notes, pts, st, cs, n_today):
    D, c = pl["dir"], pl["c"]
    alt = (f"\nClosest rival count: {cs[1]['kind']} (score {cs[1]['score']})"
           if len(cs) > 1 else "")
    return (f"{'🟢' if D > 0 else '🔴'} TRADE SIGNAL: {_side(D)} XAUUSD | "
            f"{pl['tf']} {stats.NAMES[pl['code']]}\n"
            f"Direction bias: {bias_txt}\n\n"
            f"Entry: {price:.2f} (market)\n"
            f"Stop: {pl['stop']:.2f} (risk {ev['risk']:.1f})\n"
            f"TP1: {pl['tp1']:.2f} (RR {ev['rr1']:.1f}): take 50% and move stop to entry\n"
            f"TP2: {pl['tp2']:.2f} (RR {ev['rr2']:.1f})\n\n"
            f"Quality: {pts} point(s)\n{_notes(notes)}\n\n"
            f"Count: {c['kind']} ({'; '.join(c['notes'])})\n"
            f"Plan B: {pl['plan_b']}{alt}\n"
            f"Setup record: {stats.record_line(st, pl['code'])}\n"
            f"Signal {n_today}/{config.MAX_SIGNALS_PER_DAY} today")


# ---------- state helpers ----------
def _day(st, now):
    today = now.strftime("%Y-%m-%d")
    d = st.setdefault("day", {"date": today, "n": 0})
    if d["date"] != today:
        d["date"], d["n"] = today, 0
    return d


def _open_trade(pl, price, ev, st, df5, paper):
    st.setdefault("trades", []).append(dict(
        id=int(time.time()), setup=pl["code"], tf=pl["tf"], dir=pl["dir"],
        entry=price, stop=pl["stop"], stop_now=pl["stop"],
        tp1=pl["tp1"], tp2=pl["tp2"], risk=ev["risk"], rr1=ev["rr1"], rr2=ev["rr2"],
        opened=str(df5.index[-1]), checked=str(df5.index[-1]),
        status="open", paper=paper))


# ---------- scanning ----------
def scan(df5, an, st):
    ok, _ = filters.session_ok(df5)
    if not ok:
        return
    D, bias_txt, best = trade_bias(an)
    if D is None:
        return
    now = filters.now_utc()
    if filters.news_block(now)[0]:
        return
    from analysis import get_swings as _gs
    sws = _gs()
    price = float(df5["close"].iloc[-1])
    day = _day(st, now)
    sent = st.setdefault("sent", {})
    for k in [k for k, t in sent.items() if time.time() - t > 86400]:
        del sent[k]

    for tf in config.ENTRY_TFS:
        d = tf_data(tf, df5)
        if len(d) < 30 or tf not in sws:
            continue
        a = float(atr(d).iloc[-1])
        cs = None
        from analysis import analyze as _an
        cs = an[tf]
        c = entry_count(cs)
        pl = make_plan(tf, c, D, a, sws[tf]) if c else None
        if not pl:
            continue
        mode = stats.setup_mode(st, pl["code"])
        paper = mode == "paper"
        key = f"{pl['code']}|{tf}|{c['start']}"
        trig = pl["trigger"]
        closed = float(d["close"].iloc[-2])
        triggered = (closed - trig) * D > 0 and (price - trig) * D > 0
        pts, notes, block = quality(pl, d, sws[tf], a, other_levels(an, sws, tf))
        live_open = len([t for t in st.get("trades", []) if not t.get("paper")])

        if not triggered:
            dist = (trig - price) * D
            if paper or not (0 < dist <= config.ANTICIPATE_ATR * a):
                continue
            if ("ant|" + key) in sent or day["n"] >= config.MAX_SIGNALS_PER_DAY:
                continue
            if block or pts < config.MIN_QUALITY:
                continue
            ev, _ = _eval(pl, trig)
            if not ev:
                continue
            tg.send(_ant_text(pl, ev, price, bias_txt, notes, pts, st))
            sent["ant|" + key] = time.time()
            continue

        if ("sig|" + key) in sent:
            continue
        if not paper and (day["n"] >= config.MAX_SIGNALS_PER_DAY
                          or live_open >= config.MAX_OPEN):
            continue
        ev, why = _eval(pl, price)
        if ev and (price - trig) * D > config.CHASE_FRAC * abs(trig - pl["stop"]):
            ev, why = None, "price already ran too far past the trigger (no chasing)"
        if ev and (block or pts < config.MIN_QUALITY):
            ev, why = None, block or f"quality {pts} is below {config.MIN_QUALITY}"
        sent["sig|" + key] = time.time()
        if not ev:
            if not paper:
                tg.send(f"SKIPPED: {_side(D)} {tf} {stats.NAMES[pl['code']]} triggered, "
                        f"but {why}.")
            continue
        _open_trade(pl, price, ev, st, df5, paper)
        if paper:
            continue
        day["n"] += 1
        try:
            lvl, _ = inval(c)
            png = chart.draw(d, c, f"{_side(D)} {tf} {stats.NAMES[pl['code']]}", lvl,
                             levels.fib_levels(c), levels.key_levels(sws[tf], price))
            tg.send_photo(png, f"{_side(D)} XAUUSD {price:.2f}")
        except Exception:
            pass
        tg.send(_signal_text(pl, ev, price, bias_txt, notes, pts, st, cs, day["n"]))


# ---------- trade management ----------
def _finish(t, st, outcome, R):
    stats.record(st, t["setup"], R, t.get("paper", False))
    if t.get("paper"):
        return
    s = st["stats"]
    n = s["wins"] + s["losses"]
    tg.send(f"{'✅' if R > 0 else '❌'} TRADE CLOSED: {_side(t['dir'])} XAUUSD "
            f"{t['tf']} {stats.NAMES[t['setup']]}\n"
            f"Result: {outcome} ({R:+.2f}R)\n"
            f"Record: {s['wins']}/{n} won, total {s['r']:+.1f}R")


def update_trades(df5, st):
    """Follow open trades on closed 5min candles (stop first if both hit in one candle)."""
    closed = df5.iloc[:-1]
    keep = []
    for t in st.get("trades", []):
        D, done = t["dir"], False
        for ts, row in closed[closed.index > pd.Timestamp(t["checked"])].iterrows():
            hi, lo = float(row["high"]), float(row["low"])
            stop_hit = lo <= t["stop_now"] if D > 0 else hi >= t["stop_now"]
            tp1_hit = hi >= t["tp1"] if D > 0 else lo <= t["tp1"]
            tp2_hit = hi >= t["tp2"] if D > 0 else lo <= t["tp2"]
            if t["status"] == "open":
                if stop_hit:
                    _finish(t, st, "Stopped out", -1.0)
                    done = True
                    break
                if tp1_hit:
                    t["status"], t["stop_now"] = "tp1", t["entry"]
                    if not t.get("paper"):
                        tg.send(f"🎯 TP1 HIT: {_side(D)} XAUUSD {t['tf']} "
                                f"{stats.NAMES[t['setup']]}\n"
                                f"Take 50% profit and move your stop to entry {t['entry']:.2f}.\n"
                                f"Next target TP2 {t['tp2']:.2f}.")
                    if tp2_hit:
                        _finish(t, st, "TP2 hit", 0.5 * t["rr1"] + 0.5 * t["rr2"])
                        done = True
                        break
            else:
                if stop_hit:
                    _finish(t, st, "Closed at breakeven after TP1", 0.5 * t["rr1"])
                    done = True
                    break
                if tp2_hit:
                    _finish(t, st, "TP2 hit", 0.5 * t["rr1"] + 0.5 * t["rr2"])
                    done = True
                    break
            t["checked"] = str(ts)
        if not done and len(closed):
            age_h = (closed.index[-1] - pd.Timestamp(t["opened"])).total_seconds() / 3600
            if age_h >= config.MAX_TRADE_HOURS:
                px = float(closed["close"].iloc[-1])
                run = (px - t["entry"]) * D / t["risk"]
                R = run if t["status"] == "open" else 0.5 * t["rr1"] + 0.5 * run
                _finish(t, st, f"Time exit at {px:.2f}", R)
                done = True
        if not done:
            keep.append(t)
    st["trades"] = keep


def run(df5, an, st):
    update_trades(df5, st)
    scan(df5, an, st)


# ---------- text for commands ----------
def trades_text(st):
    ts = [t for t in st.get("trades", []) if not t.get("paper")]
    if not ts:
        return "No open trades."
    lines = ["OPEN TRADES"]
    for t in ts:
        lines.append(f"{_side(t['dir'])} {t['tf']} {stats.NAMES[t['setup']]}: "
                     f"entry {t['entry']:.2f}, stop {t['stop_now']:.2f}, "
                     f"TP1 {t['tp1']:.2f}, TP2 {t['tp2']:.2f} "
                     f"[{'TP1 hit' if t['status'] == 'tp1' else 'open'}]")
    return "\n".join(lines)


def status_text(df5, an, st):
    """What the scanner sees right now, and why it is quiet or active."""
    now = filters.now_utc()
    price = float(df5["close"].iloc[-1])
    ok, why = filters.session_ok(df5)
    blocked, news = filters.news_block(now)
    D, bias_txt, _ = trade_bias(an)
    day = _day(st, now)
    live_open = len([t for t in st.get("trades", []) if not t.get("paper")])
    if D is None:
        direction = "no aligned direction, the scanner is waiting"
    else:
        direction = f"{bias_txt} -> {_side(D)} only"
    L = [f"SCANNER STATUS | XAUUSD {price:.2f}",
         f"Session: {'OK' if ok else why}",
         "News: " + (f"BLOCKED ({news})" if blocked else (news or "clear")),
         f"Direction: {direction}",
         f"Signals today: {day['n']}/{config.MAX_SIGNALS_PER_DAY}, open trades: {live_open}"]
    if D is None:
        return "\n".join(L)
    sws = get_swings()
    for tf in config.ENTRY_TFS:
        d = tf_data(tf, df5)
        a = float(atr(d).iloc[-1])
        cs = an[tf]
        c = entry_count(cs)
        if not c:
            top = f"{cs[0]['kind']} ({cs[0]['score']})" if cs else "none"
            L.append(f"\n{tf}: no clear count (top: {top})")
            continue
        pl = make_plan(tf, c, D, a, sws[tf])
        if not pl:
            L.append(f"\n{tf}: count is '{c['kind']}', no {_side(D)} setup from it")
            continue
        pts, notes, block = quality(pl, d, sws[tf], a, other_levels(an, sws, tf))
        ev, why2 = _eval(pl, pl["trigger"])
        L.append(f"\n{tf}: {stats.NAMES[pl['code']]}\n"
                 f"  trigger {pl['trigger']:.2f} (price {price:.2f}), stop {pl['stop']:.2f}, "
                 f"TP1 {pl['tp1']:.2f}\n"
                 f"  " + (f"RR {ev['rr1']:.1f}" if ev else f"filtered: {why2}") +
                 f" | quality {pts}" + (f" | BLOCKED: {block}" if block else ""))
    return "\n".join(L)

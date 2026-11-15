"""News, session, RSI, Fibonacci confluence and channel checks."""
import time
import requests
import pandas as pd
import config

NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_news = {"t": 0, "ev": None}


def now_utc():
    return pd.Timestamp.now("UTC").tz_localize(None)


def _events():
    """High-impact USD events this week (unofficial free calendar)."""
    if _news["ev"] is not None and time.time() - _news["t"] < 3600:
        return _news["ev"]
    try:
        r = requests.get(NEWS_URL, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"}).json()
        ev = [(pd.to_datetime(e["date"], utc=True).tz_localize(None), e.get("title", ""))
              for e in r if e.get("country") == "USD" and e.get("impact") == "High"]
        _news.update(t=time.time(), ev=ev)
    except Exception:
        _news["t"] = time.time() - 3000          # retry in about 10 minutes
    return _news["ev"]


def news_block(now):
    """(blocked, text). If the calendar can't be loaded, trading is not blocked."""
    ev = _events()
    if ev is None:
        return False, "news calendar unavailable"
    for t, title in ev:
        if abs((now - t).total_seconds()) <= config.NEWS_WINDOW_MIN * 60:
            return True, f"{title} at {t:%H:%M} UTC"
    return False, ""


def news_today(now):
    """List of today's high-impact events, or None if the calendar is unavailable."""
    ev = _events()
    if ev is None:
        return None
    return [f"{t:%H:%M} UTC  {title}" for t, title in sorted(ev) if t.date() == now.date()]


def session_ok(df5):
    now = now_utc()
    if (now - df5.index[-1]).total_seconds() > 1200:
        return False, "market closed or data not updating"
    lo, hi = config.TRADE_HOURS_UTC
    if now.weekday() > 4 or not (lo <= now.hour < hi):
        return False, f"outside trading hours ({lo}:00-{hi}:00 UTC, Mon-Fri)"
    return True, ""


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, 1e-9))


def divergence(d, sw):
    """'bearish', 'bullish' or None, from the last two confirmed swing highs / lows."""
    r = rsi(d["close"])
    hs = [x for x in sw[:-1] if x["k"] == "H"][-2:]
    ls = [x for x in sw[:-1] if x["k"] == "L"][-2:]
    bear = bull = -1
    if len(hs) == 2 and hs[1]["p"] > hs[0]["p"] and r.iloc[hs[1]["i"]] < r.iloc[hs[0]["i"]]:
        bear = hs[1]["i"]
    if len(ls) == 2 and ls[1]["p"] < ls[0]["p"] and r.iloc[ls[1]["i"]] > r.iloc[ls[0]["i"]]:
        bull = ls[1]["i"]
    if max(bear, bull) < len(d) - 30:            # ignore old divergences
        return None
    return "bearish" if bear > bull else "bullish"


def momentum_agrees(d, direction):
    r = float(rsi(d["close"]).iloc[-1])
    return r > 55 if direction > 0 else r < 45


def confluence(level, others, tol):
    """How many other levels sit within tol of this level."""
    return sum(1 for p in others if abs(p - level) <= tol)


def wave4_channel_ok(c, tol):
    """Wave 5 setups: did wave 4 end on the trendline through waves 0 and 2?"""
    p = c["pivots"]
    if len(p) < 5:
        return False
    t = [pd.Timestamp(x).value / 1e9 for x in c["times"]]
    if t[2] == t[0]:
        return False
    line = p[0] + (p[2] - p[0]) * (t[4] - t[0]) / (t[2] - t[0])
    return abs(p[4] - line) <= tol

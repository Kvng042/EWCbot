import config
import tg
import filters
from reports import counts_text


def maybe_send(st):
    """Once per weekday morning (UTC): counts for all timeframes and today's news."""
    now = filters.now_utc()
    today = now.strftime("%Y-%m-%d")
    h, m = config.BRIEFING_UTC
    if now.weekday() > 4 or st.get("briefed") == today:
        return
    if not ((now.hour, now.minute) >= (h, m) and now.hour < 12):
        return
    st["briefed"] = today
    news = filters.news_today(now)
    if news is None:
        news_txt = "  calendar unavailable"
    else:
        news_txt = "\n".join("  " + x for x in news) or "  none listed"
    tg.send("MORNING BRIEFING\n\n" + counts_text() +
            "\n\nHigh-impact USD news today:\n" + news_txt)

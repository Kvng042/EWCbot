import config
import state
import tg
import stats
import trader
import reports
from data import get_5m
from analysis import analyze

MENU = [[("4H analysis", "tf:4h"), ("1H analysis", "tf:1h")],
        [("15M analysis", "tf:15m"), ("5M analysis", "tf:5m")],
        [("All timeframes", "sum"), ("Scanner status", "scan")],
        [("Open trades", "trades"), ("Stats", "stats")]]


def keyboard():
    return [[{"text": t, "callback_data": d} for t, d in row] for row in MENU]


def authorized(chat):
    return str(chat) == str(config.TG_CHAT)


def show_menu(chat):
    tg.send("XAUUSD Elliott wave bot. Choose an option:", chat, keyboard())


def show_analysis(tf, chat):
    try:
        text, png, caption = reports.analysis(tf)
        if png:
            tg.send_photo(png, caption, chat)
        tg.send(text, chat, keyboard())
    except Exception as e:
        tg.send(f"Error: {e}", chat)


def _scan_text():
    df = get_5m()
    return trader.status_text(df, analyze(df), state.load())


def _reply(fn, chat):
    try:
        tg.send(fn(), chat, keyboard())
    except Exception as e:
        tg.send(f"Error: {e}", chat)


def _reset():
    s = state.load()
    keep = {k: s[k] for k in ("stats", "trades", "day", "sent", "briefed") if k in s}
    state.save(keep)
    return "Count memory cleared (trades and results kept)."


ACTIONS = {
    "/counts": reports.counts_text, "sum": reports.counts_text,
    "/scan": _scan_text, "scan": _scan_text,
    "/trades": lambda: trader.trades_text(state.load()),
    "trades": lambda: trader.trades_text(state.load()),
    "/stats": lambda: stats.text(state.load()),
    "stats": lambda: stats.text(state.load()),
    "/selftest": reports.selftest_text,
    "/reset": _reset,
}


def on_command(cmd, chat):
    if cmd == "/start" and not authorized(chat):
        tg.send(f"Your chat id is {chat}. Set it as TG_CHAT, then send /start again.", chat)
        return
    if not authorized(chat):
        return
    if cmd in ("/start", "/menu"):
        show_menu(chat)
    elif cmd in ACTIONS:
        _reply(ACTIONS[cmd], chat)


def on_button(data, chat):
    if not authorized(chat):
        return
    if data.startswith("tf:"):
        show_analysis(data[3:], chat)
    elif data in ACTIONS:
        _reply(ACTIONS[data], chat)
    else:
        show_menu(chat)

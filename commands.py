import config
import state
import tg
import reports

MENU = [[("4H analysis", "tf:4h"), ("1H analysis", "tf:1h")],
        [("15M analysis", "tf:15m"), ("5M analysis", "tf:5m")],
        [("All timeframes", "sum")]]


def keyboard():
    return [[{"text": t, "callback_data": d} for t, d in row] for row in MENU]


def authorized(chat):
    return str(chat) == str(config.TG_CHAT)


def show_menu(chat):
    tg.send("XAUUSD Elliott wave bot. Choose a timeframe:", chat, keyboard())


def show_analysis(tf, chat):
    try:
        text, png, caption = reports.analysis(tf)
        if png:
            tg.send_photo(png, caption, chat)
        tg.send(text, chat, keyboard())
    except Exception as e:
        tg.send(f"Error: {e}", chat)


def on_command(cmd, chat):
    if cmd == "/start" and not authorized(chat):
        tg.send(f"Your chat id is {chat}. Set it as TG_CHAT, then send /start again.", chat)
        return
    if not authorized(chat):
        return
    if cmd in ("/start", "/menu"):
        show_menu(chat)
    elif cmd == "/counts":
        tg.send(reports.counts_text(), chat, keyboard())
    elif cmd == "/selftest":
        try:
            tg.send(reports.selftest_text(), chat)
        except Exception as e:
            tg.send(f"Error: {e}", chat)
    elif cmd == "/reset":
        s = state.load()
        state.save({"stats": s["stats"]} if "stats" in s else {})
        tg.send("Count memory cleared (trade record kept).", chat)


def on_button(data, chat):
    if not authorized(chat):
        return
    if data.startswith("tf:"):
        show_analysis(data[3:], chat)
    elif data == "sum":
        try:
            tg.send(reports.counts_text(), chat, keyboard())
        except Exception as e:
            tg.send(f"Error: {e}", chat)
    else:
        show_menu(chat)

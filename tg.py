import time
import requests
import config

API = f"https://api.telegram.org/bot{config.TG_TOKEN}"


def send(text, chat=None, buttons=None):
    payload = {"chat_id": chat or config.TG_CHAT, "text": text}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=20)
    except Exception:
        pass


def send_photo(png, caption="", chat=None):
    try:
        requests.post(f"{API}/sendPhoto",
                      data={"chat_id": chat or config.TG_CHAT,
                            "caption": caption[:1000]},
                      files={"photo": ("chart.png", png, "image/png")},
                      timeout=60)
    except Exception:
        pass


def _answer(cb_id, text=""):
    try:
        requests.post(f"{API}/answerCallbackQuery",
                      json={"callback_query_id": cb_id, "text": text}, timeout=10)
    except Exception:
        pass


def poll(on_command, on_button):
    offset = None
    while True:
        try:
            r = requests.get(f"{API}/getUpdates",
                             params={"timeout": 50, "offset": offset},
                             timeout=60).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                cb = u.get("callback_query")
                if cb:
                    _answer(cb["id"], "Working...")
                    on_button(cb["data"], cb["message"]["chat"]["id"])
                    continue
                m = u.get("message") or {}
                txt = (m.get("text") or "").strip()
                if txt.startswith("/"):
                    on_command(txt.split()[0].split("@")[0].lower(), m["chat"]["id"])
        except Exception:
            time.sleep(5)

import os, time, threading, requests
import pandas as pd
from flask import Flask
from waves import resample, swings, find_counts

TD_KEY = os.environ.get("TD_KEY", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
API = f"https://api.telegram.org/bot{TG_TOKEN}"
TFS = {"4h": "4h", "1h": "1h", "15m": "15min", "5m": None}

app = Flask(__name__)
_cache = {"t": 0, "df": None}


def get_5m(max_age=300):
    if _cache["df"] is not None and time.time() - _cache["t"] < max_age:
        return _cache["df"]
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": "XAU/USD", "interval": "5min", "outputsize": 5000,
        "timezone": "UTC", "order": "ASC", "apikey": TD_KEY}, timeout=30).json()
    if "values" not in r:
        raise RuntimeError(str(r)[:300])
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()[["open", "high", "low", "close"]].astype(float)
    _cache.update(t=time.time(), df=df)
    return df


def tf_df(df, rule):
    return df if rule is None else resample(df, rule)


def counts_text():
    df = get_5m()
    lines = [f"XAUUSD {df['close'].iloc[-1]:.2f} ({df.index[-1]:%d %b %H:%M} UTC)"]
    for name, rule in TFS.items():
        cs = find_counts(swings(tf_df(df, rule)))
        if not cs:
            lines.append(f"\n{name}: no clear count")
            continue
        c = cs[0]
        move = "up" if c["dir"] > 0 else "down"
        alt = ""
        if len(cs) > 1 and c["score"] - cs[1]["score"] < 10:
            alt = f"\n  close alternative: {cs[1]['kind']} ({cs[1]['score']})"
        lines.append(f"\n{name}: {c['kind']}, first leg {move}, score {c['score']}\n  "
                     + "; ".join(c["notes"]) + alt)
    return "\n".join(lines)


def selftest_text():
    df = get_5m()
    lines = [f"Data OK: {len(df)} 5min candles",
             f"From {df.index[0]:%d %b %H:%M} to {df.index[-1]:%d %b %H:%M} UTC",
             f"Last price {df['close'].iloc[-1]:.2f}"]
    for name, rule in TFS.items():
        d = tf_df(df, rule)
        sw = swings(d)
        lines.append(f"{name}: {len(d)} candles, {len(sw)} swings")
    return "\n".join(lines)


def send(text, chat=None):
    try:
        requests.post(f"{API}/sendMessage",
                      json={"chat_id": chat or TG_CHAT, "text": text}, timeout=20)
    except Exception:
        pass


def handle(cmd, chat):
    if cmd == "/start":
        send(f"Elliott wave bot online. Your chat id is {chat}. "
             f"Commands: /counts /selftest", chat)
        return
    if str(chat) != str(TG_CHAT):
        return
    try:
        if cmd == "/counts":
            send(counts_text(), chat)
        elif cmd == "/selftest":
            send(selftest_text(), chat)
    except Exception as e:
        send(f"Error: {e}", chat)


def poll():
    offset = None
    while True:
        try:
            r = requests.get(f"{API}/getUpdates",
                             params={"timeout": 50, "offset": offset}, timeout=60).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                txt = (m.get("text") or "").strip()
                if txt.startswith("/"):
                    handle(txt.split()[0].split("@")[0].lower(), m["chat"]["id"])
        except Exception:
            time.sleep(5)


@app.route("/")
def home():
    return "ok"


if TG_TOKEN:
    threading.Thread(target=poll, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

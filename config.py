import os

TD_KEY = os.environ.get("TD_KEY", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
PORT = int(os.environ.get("PORT", 8000))

RESAMPLE = {"4h": "4h", "1h": "1h", "15m": "15min", "5m": None}
WATCH_TFS = ("4h", "1h", "15m")

SWING_ATR_MULT = 2.0
MIN_SCORE = 55
MIN_GAP = 8

COOLDOWN = 1200
STATE_FILE = "state.json"

import os

TD_KEY = os.environ.get("TD_KEY", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
PORT = int(os.environ.get("PORT", 8000))

RESAMPLE = {"4h": "4h", "1h": "1h", "15m": "15min", "5m": None}
WATCH_TFS = ("4h", "1h", "15m")      # timeframes used for direction and recount alerts
ENTRY_TFS = ("15m", "5m")            # timeframes the trade scanner uses for entries

# count quality
SWING_ATR_MULT = 2.0
MIN_SCORE = 55
MIN_GAP = 8
ENTRY_MIN_GAP = 4                    # entry timeframes may be a little less clear-cut

# trade rules
MIN_RR = 1.5                         # minimum reward-to-risk to TP1
MIN_STOP = 2.0                       # smallest allowed stop distance ($)
MAX_STOP = 20.0                      # largest allowed stop distance ($)
MIN_QUALITY = 1                      # minimum quality points
ANTICIPATE_ATR = 1.5                 # send anticipation when price is this many ATRs from the trigger
CHASE_FRAC = 0.5                     # skip a signal if price already ran this far past the trigger
MAX_SIGNALS_PER_DAY = 5
MAX_OPEN = 2                         # open trades at the same time
MAX_TRADE_HOURS = 6                  # close a trade at market after this long
TRADE_HOURS_UTC = (6, 21)            # trade Mon-Fri between these UTC hours
NEWS_WINDOW_MIN = 30                 # minutes before and after high-impact USD news
MIN_PROVEN = 10                      # results needed before a setup counts as proven
BRIEFING_UTC = (7, 30)

COOLDOWN = 1200
STATE_FILE = "state.json"

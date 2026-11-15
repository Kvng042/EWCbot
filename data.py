import time
import requests
import pandas as pd
import config
from swings import resample
from tg import send

_cache = {"t": 0, "df": None}
_hour = {"t": 0, "df": None}
source = {"name": "Twelve Data"}


def _yahoo(interval, rng):
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X",
        params={"interval": interval, "range": rng},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=30).json()
    res = r["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime(res["timestamp"], unit="s"))
    return df.dropna().astype(float)


def _twelve():
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": "XAU/USD", "interval": "5min", "outputsize": 5000,
        "timezone": "UTC", "order": "ASC", "apikey": config.TD_KEY},
        timeout=30).json()
    if "values" not in r:
        raise RuntimeError(str(r)[:200])
    df = pd.DataFrame(r["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    return (df.set_index("datetime").sort_index()
              [["open", "high", "low", "close"]].astype(float))


def get_5m(max_age=300):
    if _cache["df"] is not None and time.time() - _cache["t"] < max_age:
        return _cache["df"]
    try:
        df, name = _twelve(), "Twelve Data"
    except Exception:
        df, name = _yahoo("5m", "60d"), "Yahoo (backup)"
    if name != source["name"]:
        source["name"] = name
        send(f"Data source switched to {name}.")
    _cache.update(t=time.time(), df=df)
    return df


def get_hourly():
    if _hour["df"] is not None and time.time() - _hour["t"] < 3600:
        return _hour["df"]
    try:
        _hour.update(t=time.time(), df=_yahoo("60m", "120d"))
    except Exception:
        _hour["t"] = time.time() - 3000
    return _hour["df"]


def tf_data(name, df5):
    if name in ("4h", "1h"):
        h = get_hourly()
        if h is not None and len(h) > 200:
            return resample(h, "4h") if name == "4h" else h
    rule = config.RESAMPLE[name]
    return resample(df5, rule) if rule else df5

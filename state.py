import json
import config


def load():
    try:
        with open(config.STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save(s):
    try:
        with open(config.STATE_FILE, "w") as f:
            json.dump(s, f)
    except Exception:
        pass

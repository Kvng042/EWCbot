import threading
from flask import Flask
import config
import tg
import engine
import commands

app = Flask(__name__)


@app.route("/")
def home():
    return "ok"


if config.TG_TOKEN:
    threading.Thread(target=tg.poll,
                     args=(commands.on_command, commands.on_button),
                     daemon=True).start()
    threading.Thread(target=engine.loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)

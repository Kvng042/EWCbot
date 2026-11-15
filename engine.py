import time
import config
import state
import tg
import trader
import briefing
from data import get_5m
from analysis import analyze, clear, sig, inval, broken, where


def cycle():
    """Recount alerts, then the trade scanner, then the morning briefing."""
    df = get_5m()
    price = float(df["close"].iloc[-1])
    st, now, an = state.load(), time.time(), analyze(df)
    for name in config.WATCH_TFS:
        cs, old, new = an[name], st.get(name), None
        if old:
            m = next((c for c in cs if sig(c) == old["sig"]), None)
            if m and cs[0]["score"] - m["score"] < config.MIN_GAP:
                new = m
        if new is None:
            new = clear(cs)
        if old and new and sig(new) == old["sig"]:
            continue
        if not old and not new:
            continue
        if now - st.get("_last_" + name, 0) < config.COOLDOWN:
            continue
        if old:
            why = (f"price broke {old['level']:.2f}"
                   if broken(old["level"], old["side"], price)
                   else "a better-fitting count replaced it")
            msg = f"RECOUNT {name}: {old['kind']} is no longer valid ({why})."
        else:
            msg = f"{name}: new count."
        if new:
            lvl, side = inval(new)
            msg += (f"\nNew count: {new['kind']}, score {new['score']}\n"
                    + "; ".join(new["notes"])
                    + f"\nInvalid if price goes {where(side)} {lvl:.2f}")
            st[name] = dict(sig=sig(new), kind=new["kind"], level=lvl, side=side)
        else:
            msg += ("\nNo clear replacement yet. "
                    "Staying quiet on this timeframe until one forms.")
            st.pop(name, None)
        st["_last_" + name] = now
        tg.send(msg)

    try:
        trader.run(df, an, st)
    except Exception as e:
        print("trader error:", e)
    try:
        briefing.maybe_send(st)
    except Exception as e:
        print("briefing error:", e)
    state.save(st)


def loop():
    time.sleep(15)
    while True:
        try:
            cycle()
        except Exception as e:
            print("cycle error:", e)
        time.sleep(60)

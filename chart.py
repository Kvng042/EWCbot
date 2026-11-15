import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _labels(c):
    n, k = len(c["pivots"]), c["kind"]
    if n == 6:
        return ["0", "A", "B", "C", "D", "E"] if k.startswith("triangle") else list("012345")
    if n == 4: return ["0", "A", "B", "C"]
    if n == 5: return list("01234")
    if n == 3: return list("012")
    return ["0", "a", "b", "W", "X", "a", "b", "Y"]


def draw(d, c, title, inval_level, fibs, keys):
    """Candles + wave count + invalidation, fib and key levels. Returns PNG bytes."""
    pos0 = int(d.index.searchsorted(pd.Timestamp(c["times"][0])))
    start = max(0, pos0 - 12)
    if len(d) - start > 160:
        start = len(d) - 160
    v = d.iloc[start:]
    lo, hi = float(v["low"].min()), float(v["high"].max())
    rng = hi - lo
    fig, ax = plt.subplots(figsize=(8, 5.4), dpi=110)

    for i, (o, h, l, cl) in enumerate(zip(v["open"], v["high"], v["low"], v["close"])):
        col = "#16a34a" if cl >= o else "#dc2626"
        ax.vlines(i, l, h, color=col, linewidth=0.8)
        ax.add_patch(plt.Rectangle((i - 0.35, min(o, cl)), 0.7,
                                   max(abs(cl - o), 1e-6), color=col))

    xs = [max(0, int(d.index.searchsorted(pd.Timestamp(t))) - start) for t in c["times"]]
    ys = c["pivots"]
    ax.plot(xs, ys, color="#2563eb", linewidth=1.8, marker="o", markersize=4)
    for i, lab in enumerate(_labels(c)):
        above = (ys[i] >= ys[i - 1]) if i > 0 else (ys[0] > ys[1])
        ax.annotate(lab, (xs[i], ys[i]), textcoords="offset points",
                    xytext=(0, 8 if above else -14), ha="center",
                    fontsize=10, fontweight="bold", color="#1d4ed8")

    shown = [lo, hi]

    def near(p):
        return lo - 0.6 * rng <= p <= hi + 0.6 * rng

    if near(inval_level):
        ax.axhline(inval_level, color="#dc2626", linestyle="--", linewidth=1)
        ax.text(len(v) - 1, inval_level, f"invalid {inval_level:.1f} ", ha="right",
                va="bottom", fontsize=8, color="#dc2626")
        shown.append(inval_level)
    for name, p in fibs:
        if near(p):
            ax.axhline(p, color="#7c3aed", linestyle=":", linewidth=0.9)
            ax.text(0, p, f" {name} {p:.1f}", ha="left", va="bottom",
                    fontsize=7, color="#6d28d9")
            shown.append(p)
    for p in keys["res"] + keys["sup"]:
        if near(p):
            ax.axhline(p, color="#9ca3af", linestyle="-.", linewidth=0.7)
            ax.text(len(v) - 1, p, f"{p:.1f} ", ha="right", va="bottom",
                    fontsize=7, color="#4b5563")
            shown.append(p)

    pad = 0.04 * rng
    ax.set_ylim(min(shown) - pad, max(shown) + pad)
    ax.set_xlim(-1, len(v) + 1)
    idx = np.linspace(0, len(v) - 1, 6).astype(int)
    ax.set_xticks(idx)
    ax.set_xticklabels(v.index[idx].strftime("%d %H:%M"), fontsize=8)
    ax.set_title(title, fontsize=11)
    ax.grid(alpha=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

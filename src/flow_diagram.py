"""Draw a vertical funnel flow diagram (steps, % continuing, users lost per step)
from the tables written by analysis.py."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "reports" / "tables"
OUT = ROOT / "charts" / "06_funnel_flow.png"

BLUE, RED, DARK = "#4C72B0", "#C44E52", "#222222"


def box(ax, cx, cy, w, h, text, fc, tc="white", fs=10, weight="bold", alpha=1.0):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=fc, ec="none", alpha=alpha))
    ax.text(cx, cy, text, ha="center", va="center", color=tc, fontsize=fs, weight=weight, linespacing=1.3)


def main():
    f = pd.read_csv(T / "01_overall_funnel.csv")
    dev = pd.read_csv(T / "03_by_device.csv").set_index("device")
    wk = pd.read_csv(T / "04_weekly_trend.csv")
    mob = wk[wk["device"] == "mobile"]
    dip = mob[mob["payment_to_purchase_pct"] < 70]

    # extra notes attached to specific transitions (by index of the lower step)
    notes = {
        4: f"Mobile {dev.loc['mobile', 'checkout_to_payment_pct']:.0f}% vs desktop "
           f"{dev.loc['desktop', 'checkout_to_payment_pct']:.0f}% reach payment",
        5: (f"Mobile dip, weeks of {pd.to_datetime(dip['week_start']).min():%b %d} & "
            f"{pd.to_datetime(dip['week_start']).max():%b %d}:\n"
            f"only {dip['payment_to_purchase_pct'].min():.0f}-{dip['payment_to_purchase_pct'].max():.0f}% completed")
        if len(dip) else "",
    }

    n = len(f)
    fig, ax = plt.subplots(figsize=(8, 11))
    ax.set_xlim(0, 10); ax.set_ylim(-0.6, 2 * n + 0.6); ax.axis("off")
    ys = [2 * (n - 1 - i) + 0.9 for i in range(n)]
    top = f["users"].max()

    for i, r in f.iterrows():
        w = 1.9 + 2.3 * r["users"] / top
        label = f"{r['step']}\n{int(r['users']):,}  ({r['overall_pct']:.1f}%)"
        box(ax, 2.6, ys[i], w, 1.05, label, BLUE, fs=10)

        if i > 0:
            mid = (ys[i] + ys[i - 1]) / 2 + 0.0
            ax.annotate("", xy=(2.6, ys[i] + 0.55), xytext=(2.6, ys[i - 1] - 0.55),
                        arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1.4))
            ax.text(2.45, mid, f"{r['step_conv_pct']:.0f}% continue", ha="right", va="center",
                    fontsize=9, color=DARK)
            lost = int(f.loc[i - 1, "users"] - r["users"])
            txt = f"-{lost:,} lost  ({r['dropoff_pct']:.0f}%)"
            extra = notes.get(i, "")
            h = 0.8 + 0.3 * (extra.count("\n") + 1 if extra else 0)
            box(ax, 7.55, mid, 4.8, h, txt + (f"\n{extra}" if extra else ""),
                RED, fs=9, alpha=0.35 + 0.65 * min(r["dropoff_pct"] / 70, 1))
            ax.annotate("", xy=(5.3, mid), xytext=(2.6, mid),
                        arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.0, ls="--"))

    ax.text(0.1, 2 * n + 0.35,
            f"Where shoppers drop off: {int(f['users'].iloc[0]):,} visitors -> {int(f['users'].iloc[-1]):,} buyers",
            fontsize=13, weight="bold", ha="left")
    ax.text(0.1, -0.4, "Unique users, ordered steps, 7-day window. Synthetic data. Darker red = bigger drop.",
            fontsize=8, color="#555", ha="left")
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print("saved", OUT)


if __name__ == "__main__":
    main()

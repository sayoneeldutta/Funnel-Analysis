"""Load the clickstream into SQLite, run the funnel SQL, save tables and charts."""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, SQL, CHARTS, TABLES = ROOT / "data", ROOT / "sql", ROOT / "charts", ROOT / "reports" / "tables"
DB = DATA / "funnel.db"
BLUE, ORANGE, GREEN = "#4C72B0", "#DD8452", "#55A868"
DEVICE_COLORS = {"mobile": ORANGE, "desktop": BLUE, "tablet": GREEN}

plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})


def build_db() -> sqlite3.Connection:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    pd.read_csv(DATA / "users.csv").to_sql("users", con, index=False)
    pd.read_csv(DATA / "events.csv").to_sql("events", con, index=False)
    con.execute("CREATE INDEX idx_events_user ON events(user_id, event_name)")
    con.executescript((SQL / "00_user_funnel_view.sql").read_text())
    return con


def q(con, name: str) -> pd.DataFrame:
    df = pd.read_sql_query((SQL / name).read_text(), con)
    df.to_csv(TABLES / name.replace(".sql", ".csv"), index=False)
    return df


def chart_funnel(df):
    fig, ax = plt.subplots(figsize=(9, 4.8))
    y = np.arange(len(df))[::-1]
    ax.barh(y, df["users"], color=BLUE)
    for yi, r in zip(y, df.itertuples()):
        extra = "" if pd.isna(r.step_conv_pct) else f"  |  {r.step_conv_pct:.0f}% of previous"
        ax.text(r.users + df["users"].max() * 0.01, yi,
                f"{r.users:,} ({r.overall_pct:.1f}%){extra}", va="center")
    ax.set_yticks(y, df["step"])
    ax.set_xlim(0, df["users"].max() * 1.65)
    ax.set_title("Overall conversion funnel (unique users, 7-day window)", loc="left", weight="bold")
    ax.set_xlabel("Users")
    fig.tight_layout()
    fig.savefig(CHARTS / "01_funnel.png", dpi=150)
    plt.close(fig)


def chart_channel(df):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    d = df.sort_values("overall_conv_pct")
    bars = ax.barh(d["channel"], d["overall_conv_pct"], color=BLUE)
    ax.bar_label(bars, labels=[f"{v:.2f}%" for v in d["overall_conv_pct"]], padding=3)
    ax.set_xlim(0, d["overall_conv_pct"].max() * 1.2)
    ax.set_title("Visit-to-purchase conversion by channel", loc="left", weight="bold")
    ax.set_xlabel("% of visitors who purchase")
    fig.tight_layout()
    fig.savefig(CHARTS / "02_channel_conversion.png", dpi=150)
    plt.close(fig)


def chart_device(df):
    pairs = [("Visit→View", "product_views", "visits"), ("View→Cart", "add_to_cart", "product_views"),
             ("Cart→Checkout", "checkout", "add_to_cart"), ("Checkout→Payment", "payment", "checkout"),
             ("Payment→Purchase", "purchases", "payment")]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    x, w = np.arange(len(pairs)), 0.26
    for i, dev in enumerate(["mobile", "desktop", "tablet"]):
        row = df[df["device"] == dev].iloc[0]
        vals = [100 * row[a] / row[b] for _, a, b in pairs]
        ax.bar(x + (i - 1) * w, vals, w, label=dev, color=DEVICE_COLORS[dev])
    ax.set_xticks(x, [p[0] for p in pairs])
    ax.set_ylabel("Step conversion (%)")
    ax.set_title("Step conversion by device: mobile leaks at checkout → payment", loc="left", weight="bold")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "03_device_step_conversion.png", dpi=150)
    plt.close(fig)


def chart_weekly(df):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, col, title in [(axes[0], "overall_conv_pct", "Visit→Purchase % by first-visit week"),
                           (axes[1], "payment_to_purchase_pct", "Payment→Purchase % by first-visit week")]:
        for dev in ["mobile", "desktop"]:
            d = df[df["device"] == dev]
            ax.plot(pd.to_datetime(d["week_start"]), d[col], marker="o", label=dev, color=DEVICE_COLORS[dev])
        ax.set_title(title, loc="left", weight="bold", fontsize=10)
        ax.tick_params(axis="x", rotation=30)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "04_weekly_trend.png", dpi=150)
    plt.close(fig)


def chart_ttc(minutes):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(minutes, bins=np.logspace(0, np.log10(minutes.max()), 50), color=BLUE)
    ax.set_xscale("log")
    ax.axvline(minutes.median(), color=ORANGE, ls="--", label=f"median = {minutes.median():.0f} min")
    ax.set_xlabel("Minutes from first visit to purchase (log scale)")
    ax.set_ylabel("Purchasers")
    ax.set_title("Time to convert", loc="left", weight="bold")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "05_time_to_convert.png", dpi=150)
    plt.close(fig)


def main():
    CHARTS.mkdir(exist_ok=True); TABLES.mkdir(parents=True, exist_ok=True)
    con = build_db()
    overall, by_ch = q(con, "01_overall_funnel.sql"), q(con, "02_by_channel.sql")
    by_dev, weekly = q(con, "03_by_device.sql"), q(con, "04_weekly_trend.sql")
    t = pd.read_sql_query("SELECT t1, t6 FROM user_funnel WHERE r6 = 1", con)
    minutes = (pd.to_datetime(t["t6"]) - pd.to_datetime(t["t1"])).dt.total_seconds() / 60

    chart_funnel(overall); chart_channel(by_ch); chart_device(by_dev); chart_weekly(weekly); chart_ttc(minutes)

    raw = pd.read_sql_query("SELECT COUNT(*) n, COUNT(DISTINCT user_id||event_name) uniq FROM events", con).iloc[0]
    summary = [
        "OVERALL FUNNEL", overall.to_string(index=False),
        "\nBY CHANNEL", by_ch.to_string(index=False),
        "\nBY DEVICE", by_dev.to_string(index=False),
        "\nWEEKLY (mobile payment->purchase)",
        weekly[weekly.device == "mobile"][["week_start", "overall_conv_pct", "payment_to_purchase_pct"]].to_string(index=False),
        f"\nTIME TO CONVERT (min): median={minutes.median():.0f}  p90={minutes.quantile(.9):.0f}",
        f"\nDATA QUALITY: {int(raw.n):,} event rows, {int(raw.uniq):,} unique user-event pairs "
        f"-> {int(raw.n - raw.uniq):,} duplicates handled by MIN() in the view",
    ]
    text = "\n".join(summary)
    (ROOT / "reports" / "summary.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()

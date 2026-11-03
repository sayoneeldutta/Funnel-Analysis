"""Generate a synthetic e-commerce clickstream for funnel analysis.

Planted patterns (so the analysis has real stories to find):
  1. Mobile users drop hard between checkout_start and payment_info.
  2. paid_search brings lots of traffic but weak engagement; email converts best.
  3. A mobile payment bug in weeks 8-9 temporarily crushes payment -> purchase.
  4. ~3% duplicate event rows (double-fired tracking) to practise de-duplication.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_USERS = 60_000
START = pd.Timestamp("2026-08-03")   # a Monday
DAYS = 84                            # 12 full weeks of first visits
BUG_DAYS = (49, 63)                  # [start, end) day index of the mobile payment bug

STEPS = ["session_start", "product_view", "add_to_cart",
         "checkout_start", "payment_info", "purchase"]

CHANNELS = {"organic": .30, "paid_search": .25, "social": .20, "email": .15, "referral": .10}
DEVICES = {"mobile": .62, "desktop": .33, "tablet": .05}

# Step probabilities, conditional on reaching the previous step
VIEW_BASE, CART_BASE, CHECKOUT_BASE, PURCHASE_BASE = 0.72, 0.30, 0.60, 0.86
VIEW_BY_CH = {"organic": 1.05, "paid_search": 0.85, "social": 0.95, "email": 1.15, "referral": 1.10}
CART_BY_CH = {"organic": 1.00, "paid_search": 0.90, "social": 0.65, "email": 1.40, "referral": 1.20}
PURCHASE_BY_CH = {"organic": 1.00, "paid_search": 0.97, "social": 0.95, "email": 1.08, "referral": 1.03}
PAYMENT_BY_DEVICE = {"mobile": 0.52, "desktop": 0.80, "tablet": 0.70}

# Mean minutes between a step and the one before it
LAG_MIN = {1: 2, 2: 10, 3: 12, 4: 4, 5: 3}


def main() -> None:
    rng = np.random.default_rng(SEED)
    out = Path(__file__).resolve().parents[1] / "data"
    out.mkdir(exist_ok=True)

    users = pd.DataFrame({
        "user_id": np.arange(1, N_USERS + 1),
        "channel": rng.choice(list(CHANNELS), N_USERS, p=list(CHANNELS.values())),
        "device": rng.choice(list(DEVICES), N_USERS, p=list(DEVICES.values())),
    })
    day = rng.integers(0, DAYS, N_USERS)
    t0 = (START + pd.to_timedelta(day, unit="D")
          + pd.to_timedelta(rng.integers(0, 86_400, N_USERS), unit="s"))
    users["first_seen_date"] = t0.strftime("%Y-%m-%d")

    ch, dv = users["channel"], users["device"]
    is_mobile = (dv == "mobile").to_numpy()
    in_bug = is_mobile & (day >= BUG_DAYS[0]) & (day < BUG_DAYS[1])

    p = {
        1: VIEW_BASE * ch.map(VIEW_BY_CH).to_numpy(),
        2: CART_BASE * ch.map(CART_BY_CH).to_numpy(),
        3: np.full(N_USERS, CHECKOUT_BASE),
        4: dv.map(PAYMENT_BY_DEVICE).to_numpy(),
        5: PURCHASE_BASE * ch.map(PURCHASE_BY_CH).to_numpy(),
    }
    p[5] = np.where(in_bug, 0.55, p[5])
    p = {k: np.clip(v, 0, 0.98) for k, v in p.items()}

    frames, reached, ts = [], np.ones(N_USERS, bool), t0
    for k, step in enumerate(STEPS):
        if k > 0:
            reached &= rng.random(N_USERS) < p[k]
            lag = rng.exponential(LAG_MIN[k], N_USERS)
            if step == "checkout_start":  # some people come back days later
                returner = rng.random(N_USERS) < 0.18
                lag = lag + returner * rng.exponential(1.5 * 1440, N_USERS)
            ts = ts + pd.to_timedelta(lag, unit="m")
        idx = np.flatnonzero(reached)
        frames.append(pd.DataFrame({
            "user_id": users["user_id"].to_numpy()[idx],
            "event_name": step,
            "event_ts": ts[idx],
        }))

    events = pd.concat(frames, ignore_index=True)
    events["event_ts"] = events["event_ts"].dt.floor("s")

    dup = events.sample(frac=0.03, random_state=SEED).copy()   # double-fired tracking
    dup["event_ts"] += pd.to_timedelta(rng.integers(0, 6, len(dup)), unit="s")
    events = (pd.concat([events, dup], ignore_index=True)
                .sort_values(["event_ts", "user_id"]).reset_index(drop=True))
    events.insert(0, "event_id", np.arange(1, len(events) + 1))
    events["event_ts"] = events["event_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

    users.to_csv(out / "users.csv", index=False)
    events.to_csv(out / "events.csv", index=False)
    print(f"users:  {len(users):,}\nevents: {len(events):,}  (incl. {len(dup):,} duplicates)")


if __name__ == "__main__":
    main()

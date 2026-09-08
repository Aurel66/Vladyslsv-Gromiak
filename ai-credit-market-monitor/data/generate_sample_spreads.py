"""
Generates data/sample_spreads.csv: a synthetic, illustrative 60-business-day
history of credit spreads (bps over benchmark) for each issuer in
sample_issuers.csv.

This is NOT real market data. It exists so the pipeline can be demoed and
tested without a live market data feed. Two issuers are seeded with a
deliberate event (a sharp widening and a sharp tightening) so the flagging
logic in src/credit_metrics.py has something real to catch.

Run once: python data/generate_sample_spreads.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

ISSUERS = {
    "ATMC": {"start_spread": 310, "drift": 0.0, "vol": 4.0},
    "MERE": {"start_spread": 165, "drift": 0.0, "vol": 2.5},
    "NFTC": {"start_spread": 140, "drift": 0.0, "vol": 2.0},
    # Deliberate stress event: cruise-line credit widens sharply mid-period
    "AURC": {"start_spread": 420, "drift": 0.0, "vol": 5.0, "event_day": 38, "event_bps": 95},
    "FALC": {"start_spread": 120, "drift": 0.0, "vol": 2.0},
    "SLRG": {"start_spread": 340, "drift": 0.0, "vol": 4.5},
    "VTEU": {"start_spread": 180, "drift": 0.0, "vol": 2.5},
    # Deliberate improvement: streaming credit tightens on a strong outlook
    "CRST": {"start_spread": 300, "drift": 0.0, "vol": 3.5, "event_day": 45, "event_bps": -60},
    "HRLN": {"start_spread": 145, "drift": 0.0, "vol": 2.0},
    "CPRU": {"start_spread": 110, "drift": 0.0, "vol": 1.8},
    "STRT": {"start_spread": 265, "drift": 0.0, "vol": 3.5},
    "NXRA": {"start_spread": 125, "drift": 0.0, "vol": 2.2},
    "WCPH": {"start_spread": 150, "drift": 0.0, "vol": 2.0},
    # Deliberate stress event: mining credit widens sharply on commodity weakness
    "IRPK": {"start_spread": 380, "drift": 0.0, "vol": 5.0, "event_day": 42, "event_bps": 70},
    "DLCH": {"start_spread": 210, "drift": 0.0, "vol": 2.8},
    "BRCS": {"start_spread": 95, "drift": 0.0, "vol": 1.5},
}

N_DAYS = 60


def business_days(n, start=None):
    d = start or date.today() - timedelta(days=int(n * 1.45))
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def main():
    dates = business_days(N_DAYS)
    rows = []
    for ticker, cfg in ISSUERS.items():
        spread = cfg["start_spread"]
        event_day = cfg.get("event_day")
        event_bps = cfg.get("event_bps", 0)
        for i, d in enumerate(dates):
            spread += random.gauss(cfg["drift"], cfg["vol"])
            if event_day is not None and i == event_day:
                spread += event_bps
            spread = max(spread, 20)
            rows.append({"date": d.isoformat(), "ticker": ticker, "spread_bps": round(spread, 1)})

    out_path = Path(__file__).parent / "sample_spreads.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "ticker", "spread_bps"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

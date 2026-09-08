"""
Data loading for the Credit Market Monitor.

Two modes:

- load_sample_*()   Reads the synthetic CSVs committed under data/. Always
                     works offline, no keys required. Used by default so the
                     tool is demoable out of the box.

- fetch_live_*()    Real connectors against free public sources (Yahoo
                     Finance via yfinance, FRED via its public CSV endpoint).
                     These are a reasonable starting point but are NOT a
                     substitute for what a real credit desk uses (Bloomberg,
                     ICE/Markit, Refinitiv) for single-name bond/CDS spreads
                     and clean fundamentals. They're wired up so the same
                     pipeline can be pointed at better data sources later by
                     swapping the function that returns these DataFrames.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REQUIRED_ISSUER_COLUMNS = [
    "issuer", "ticker", "sector", "region", "rating",
    "total_debt_usd_mm", "ebitda_usd_mm", "ebit_usd_mm", "interest_expense_usd_mm",
]
REQUIRED_SPREAD_COLUMNS = ["date", "ticker", "spread_bps"]


def load_sample_issuers() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "sample_issuers.csv")
    missing = set(REQUIRED_ISSUER_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"sample_issuers.csv missing columns: {missing}")
    return df


def load_sample_spreads() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "sample_spreads.csv", parse_dates=["date"])
    missing = set(REQUIRED_SPREAD_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"sample_spreads.csv missing columns: {missing}")
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def fetch_fred_series(series_id: str, timeout: int = 10) -> pd.DataFrame:
    """
    Pull a public FRED series as a market-backdrop benchmark, e.g.
    'BAMLC0A0CM' (ICE BofA US Corporate Index OAS) or
    'BAMLH0A0HYM2' (ICE BofA US High Yield Index OAS).

    Uses FRED's public CSV export endpoint — no API key required. Returns a
    two-column DataFrame: date, value (in the series' native units, usually %).
    """
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def fetch_yfinance_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """
    Best-effort fundamentals pull via yfinance for a list of equity tickers
    of the parent/guarantor entity (credit desks generally trade the bonds
    of listed corporates, so the equity ticker's balance sheet is a usable
    proxy when a dedicated credit data feed isn't available).

    yfinance coverage of totalDebt/ebitda/ebit varies by issuer and is not
    reliable enough to trade on — treat this as a starting point, not a
    source of truth.
    """
    import yfinance as yf  # optional dependency, only needed for live mode

    rows = []
    for t in tickers:
        info = yf.Ticker(t).info
        rows.append({
            "ticker": t,
            "total_debt_usd_mm": (info.get("totalDebt") or 0) / 1e6,
            "ebitda_usd_mm": (info.get("ebitda") or 0) / 1e6,
            "market_cap_usd_mm": (info.get("marketCap") or 0) / 1e6,
        })
    return pd.DataFrame(rows)

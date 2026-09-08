"""
Credit metric calculations and flagging logic.

Deliberately simple, transparent thresholds rather than a black-box model —
the point of this tool is to speed up a human credit analyst's morning
triage, not to replace their judgement. Every flag traces back to a
metric you can sanity-check by eye.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# Rough, sector-agnostic triage thresholds. A real desk would set these
# per-sector and per-rating-band; kept flat here for clarity.
LEVERAGE_CAUTION = 4.5      # Total Debt / EBITDA
LEVERAGE_HIGH_RISK = 6.0
COVERAGE_CAUTION = 3.0      # EBIT / Interest Expense
COVERAGE_HIGH_RISK = 2.0
SPREAD_MOVE_CAUTION_BPS = 25    # absolute 5-business-day move
SPREAD_MOVE_HIGH_RISK_BPS = 60


@dataclass
class IssuerAssessment:
    ticker: str
    issuer: str
    sector: str
    rating: str
    leverage: float
    interest_coverage: float
    latest_spread_bps: float
    spread_5d_change_bps: float
    spread_30d_change_bps: float
    flags: list[str] = field(default_factory=list)

    @property
    def is_flagged(self) -> bool:
        return len(self.flags) > 0

    @property
    def severity(self) -> str:
        if any("HIGH RISK" in f for f in self.flags):
            return "HIGH RISK"
        if self.flags:
            return "CAUTION"
        return "STABLE"


def compute_leverage(total_debt_usd_mm: float, ebitda_usd_mm: float) -> float:
    if ebitda_usd_mm <= 0:
        return float("inf")
    return total_debt_usd_mm / ebitda_usd_mm


def compute_interest_coverage(ebit_usd_mm: float, interest_expense_usd_mm: float) -> float:
    if interest_expense_usd_mm <= 0:
        return float("inf")
    return ebit_usd_mm / interest_expense_usd_mm


def spread_change(spreads: pd.DataFrame, ticker: str, lookback_days: int) -> float:
    s = spreads[spreads["ticker"] == ticker].sort_values("date")
    if len(s) <= lookback_days:
        return 0.0
    latest = s["spread_bps"].iloc[-1]
    prior = s["spread_bps"].iloc[-1 - lookback_days]
    return round(latest - prior, 1)


def assess_issuer(issuer_row: pd.Series, spreads: pd.DataFrame) -> IssuerAssessment:
    leverage = compute_leverage(issuer_row["total_debt_usd_mm"], issuer_row["ebitda_usd_mm"])
    coverage = compute_interest_coverage(issuer_row["ebit_usd_mm"], issuer_row["interest_expense_usd_mm"])
    ticker = issuer_row["ticker"]

    issuer_spreads = spreads[spreads["ticker"] == ticker].sort_values("date")
    latest_spread = float(issuer_spreads["spread_bps"].iloc[-1])
    change_5d = spread_change(spreads, ticker, 5)
    change_30d = spread_change(spreads, ticker, 30)

    flags: list[str] = []
    if leverage >= LEVERAGE_HIGH_RISK:
        flags.append(f"HIGH RISK: leverage {leverage:.1f}x >= {LEVERAGE_HIGH_RISK}x")
    elif leverage >= LEVERAGE_CAUTION:
        flags.append(f"CAUTION: leverage {leverage:.1f}x >= {LEVERAGE_CAUTION}x")

    if coverage <= COVERAGE_HIGH_RISK:
        flags.append(f"HIGH RISK: interest coverage {coverage:.1f}x <= {COVERAGE_HIGH_RISK}x")
    elif coverage <= COVERAGE_CAUTION:
        flags.append(f"CAUTION: interest coverage {coverage:.1f}x <= {COVERAGE_CAUTION}x")

    if abs(change_5d) >= SPREAD_MOVE_HIGH_RISK_BPS:
        direction = "widened" if change_5d > 0 else "tightened"
        flags.append(f"HIGH RISK: spread {direction} {abs(change_5d):.0f}bps in 5 days")
    elif abs(change_5d) >= SPREAD_MOVE_CAUTION_BPS:
        direction = "widened" if change_5d > 0 else "tightened"
        flags.append(f"CAUTION: spread {direction} {abs(change_5d):.0f}bps in 5 days")

    return IssuerAssessment(
        ticker=ticker,
        issuer=issuer_row["issuer"],
        sector=issuer_row["sector"],
        rating=issuer_row["rating"],
        leverage=round(leverage, 2),
        interest_coverage=round(coverage, 2),
        latest_spread_bps=latest_spread,
        spread_5d_change_bps=change_5d,
        spread_30d_change_bps=change_30d,
        flags=flags,
    )


def assess_universe(issuers: pd.DataFrame, spreads: pd.DataFrame) -> list[IssuerAssessment]:
    return [assess_issuer(row, spreads) for _, row in issuers.iterrows()]

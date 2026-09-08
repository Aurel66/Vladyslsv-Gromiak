import pandas as pd
import pytest

from src.credit_metrics import (
    compute_interest_coverage,
    compute_leverage,
    assess_issuer,
    spread_change,
)


def test_compute_leverage_normal():
    assert compute_leverage(total_debt_usd_mm=4000, ebitda_usd_mm=1000) == 4.0


def test_compute_leverage_zero_ebitda_is_infinite():
    assert compute_leverage(total_debt_usd_mm=100, ebitda_usd_mm=0) == float("inf")


def test_compute_interest_coverage_normal():
    assert compute_interest_coverage(ebit_usd_mm=600, interest_expense_usd_mm=200) == 3.0


def test_compute_interest_coverage_zero_interest_is_infinite():
    assert compute_interest_coverage(ebit_usd_mm=100, interest_expense_usd_mm=0) == float("inf")


@pytest.fixture
def spreads():
    rows = [
        {"date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i), "ticker": "TEST", "spread_bps": 100 + i}
        for i in range(10)
    ]
    return pd.DataFrame(rows)


def test_spread_change_5d(spreads):
    # day 9 value is 109, day 4 value is 104 -> +5
    assert spread_change(spreads, "TEST", 5) == 5.0


def test_spread_change_insufficient_history_returns_zero(spreads):
    assert spread_change(spreads, "TEST", 20) == 0.0


def test_assess_issuer_flags_high_leverage(spreads):
    issuer_row = pd.Series({
        "ticker": "TEST", "issuer": "Test Co", "sector": "Test", "rating": "B",
        "total_debt_usd_mm": 7000, "ebitda_usd_mm": 1000,  # 7.0x -> HIGH RISK
        "ebit_usd_mm": 500, "interest_expense_usd_mm": 100,  # 5.0x -> stable coverage
    })
    result = assess_issuer(issuer_row, spreads)
    assert result.is_flagged
    assert result.severity == "HIGH RISK"
    assert any("leverage" in f for f in result.flags)


def test_assess_issuer_stable_when_nothing_breaches_thresholds(spreads):
    issuer_row = pd.Series({
        "ticker": "TEST", "issuer": "Test Co", "sector": "Test", "rating": "A",
        "total_debt_usd_mm": 1000, "ebitda_usd_mm": 1000,  # 1.0x
        "ebit_usd_mm": 500, "interest_expense_usd_mm": 50,  # 10.0x
    })
    result = assess_issuer(issuer_row, spreads)
    assert not result.is_flagged
    assert result.severity == "STABLE"

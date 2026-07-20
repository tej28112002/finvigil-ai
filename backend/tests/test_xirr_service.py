"""
Unit tests for the XIRR math algorithm.  No DB, no network.

Expected values are hand-computed from first principles (NPV = 0 definition)
not derived by running the code under test, so a test failure here means
the algorithm is wrong, not just that the expected value was copied wrong.
"""
from datetime import date
from decimal import Decimal

from app.services.xirr_service import _run_xirr_cashflows


def test_xirr_basic_one_year_eighteen_percent():
    """
    Exactly 365 days between buy and terminal value; 18 % gain.
    Hand-check: NPV(0.18) = -100000 + 118000/1.18 = -100000 + 100000 = 0.
    """
    buy_date = date(2024, 6, 1)
    end_date = date(2025, 6, 1)  # 365 days
    cashflows = [
        (buy_date, Decimal("-100000")),
        (end_date, Decimal("118000")),
    ]
    result = _run_xirr_cashflows(cashflows)
    assert result is not None
    assert abs(result - 0.18) < 0.001


def test_xirr_with_partial_sell_and_remaining_value():
    """
    Buy → partial sell 6 months later → terminal value at ~1.5 years.
    Total cash in: 100000, total cash out: 30000 + 85000 = 115000.
    Expected: modest positive return; result must be a finite float in [-1, 10].
    """
    cashflows = [
        (date(2024, 1, 1), Decimal("-100000")),
        (date(2024, 7, 1), Decimal("30000")),
        (date(2025, 7, 1), Decimal("85000")),
    ]
    result = _run_xirr_cashflows(cashflows)
    assert result is not None
    assert isinstance(result, float)
    assert -1.0 < result < 10.0


def test_xirr_returns_none_for_single_cashflow():
    """
    NPV of a single negative cashflow is always negative → brentq finds no
    sign change → ValueError → None.
    """
    cashflows = [(date(2024, 1, 1), Decimal("-100000"))]
    result = _run_xirr_cashflows(cashflows)
    assert result is None


def test_xirr_returns_none_when_all_cashflows_are_negative():
    """
    All outflows (user bought but current portfolio value is somehow zero).
    NPV is always negative for any rate > -1 → no sign change → None.
    """
    cashflows = [
        (date(2024, 1, 1), Decimal("-100000")),
        (date(2024, 6, 1), Decimal("-50000")),
    ]
    result = _run_xirr_cashflows(cashflows)
    assert result is None

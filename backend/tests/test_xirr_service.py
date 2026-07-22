"""
Unit tests for the XIRR math algorithm.  No DB, no network.

Expected values are hand-computed from first principles (NPV = 0 definition)
not derived by running the code under test, so a test failure here means
the algorithm is wrong, not just that the expected value was copied wrong.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.xirr_service import XirrService, _run_xirr_cashflows
from tests.fakes import (
    FakeDashboardProjection,
    FakeDashboardRepository,
    FakeHoldingLotRepository,
    FakeInstrument,
    FakeLot,
    FakeRealizedGainRepository,
)


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


def test_compute_absolute_return_known_values():
    """
    invested = 100 units * 1000 = 100000. current_value (from the dashboard
    projection) = 118000. No realized gains yet.
    Expected: (118000 - 100000) / 100000 * 100 = 18.0 %.
    """
    lot = FakeLot(
        quantity_remaining=Decimal("100"),
        buy_price=Decimal("1000"),
        buy_date=datetime(2024, 1, 1),
    )
    service = XirrService(
        trade_repository=None,
        holding_repository=FakeHoldingLotRepository([lot]),
        dashboard_repository=FakeDashboardRepository(
            FakeDashboardProjection(total_equity_value=Decimal("118000"))
        ),
        nifty_service=None,
        realized_gain_repository=FakeRealizedGainRepository([]),
    )
    result = service.compute_absolute_return(uuid4())
    assert result is not None
    assert abs(result - 18.0) < 0.01


def test_compute_cagr_two_years():
    """
    invested = 100000, current_value = 144000, exactly 730 days (2.0 years)
    since the earliest buy.
    Hand-check: (144000/100000)^(1/2) - 1 = sqrt(1.44) - 1 = 1.2 - 1 = 0.20.
    Expected CAGR ~= 20.0 %.
    """
    earliest = date.today() - timedelta(days=730)
    lot = FakeLot(
        quantity_remaining=Decimal("100"),
        buy_price=Decimal("1000"),
        buy_date=datetime.combine(earliest, datetime.min.time()),
    )
    service = XirrService(
        trade_repository=None,
        holding_repository=FakeHoldingLotRepository([lot]),
        dashboard_repository=FakeDashboardRepository(
            FakeDashboardProjection(total_equity_value=Decimal("144000"))
        ),
        nifty_service=None,
        realized_gain_repository=FakeRealizedGainRepository([]),
    )
    result = service.compute_cagr(uuid4())
    assert result is not None
    assert abs(result - 20.0) < 0.01


def test_compute_asset_allocation_sums_to_100():
    """Two equity lots + one crypto lot; weights must sum to ~100%
    regardless of how many instrument types are present."""
    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime(2024, 1, 1),
            instrument=FakeInstrument(symbol="RELIANCE", instrument_type="equity"),
        ),
        FakeLot(
            quantity_remaining=Decimal("5"),
            buy_price=Decimal("200"),
            buy_date=datetime(2024, 2, 1),
            instrument=FakeInstrument(symbol="TCS", instrument_type="equity"),
        ),
        FakeLot(
            quantity_remaining=Decimal("1"),
            buy_price=Decimal("500"),
            buy_date=datetime(2024, 3, 1),
            instrument=FakeInstrument(symbol="BTC", instrument_type="crypto"),
        ),
    ]
    service = XirrService(
        trade_repository=None,
        holding_repository=FakeHoldingLotRepository(lots),
        dashboard_repository=None,
        nifty_service=None,
        realized_gain_repository=None,
    )
    result = service.compute_asset_allocation(uuid4())
    assert result is not None
    assert abs(sum(result.values()) - 100.0) < 0.01

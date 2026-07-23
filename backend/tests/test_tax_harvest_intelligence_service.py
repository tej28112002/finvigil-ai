"""
Unit tests for TaxHarvestingIntelligenceService. No DB, no network — uses
FakeGain / FakeLot / FakeHoldingLotRepository / FakeRealizedGainRepository
from tests/fakes.py.

Expected values are hand-computed from Section 70 set-off rules and the
service's own documented formulas (its own design, not external law being
re-derived) -- a failure here means the algorithm is wrong, not that the
expected value was copied from the code under test.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.tax_harvest_intelligence_service import (
    TaxHarvestingIntelligenceService,
)
from tests.fakes import FakeGain, FakeHoldingLotRepository, FakeInstrument, FakeLot, FakeRealizedGainRepository


def _service(
    gains: list[FakeGain] | None = None,
    lots: list[FakeLot] | None = None,
) -> TaxHarvestingIntelligenceService:
    return TaxHarvestingIntelligenceService(
        realized_gain_repository=FakeRealizedGainRepository(gains or []),
        holding_lot_repository=FakeHoldingLotRepository(lots or []),
        dashboard_repository=None,
    )


def test_fy_summary_with_mixed_gains_and_losses():
    """
    LTCG +80000, STCG +30000, STCG loss -20000, LTCG loss -10000.
    net_stcg = 30000 - 20000 = 10000, stcg_loss_remainder = 0.
    net_ltcg = 80000 - 10000 - 0 = 70000.
    exemption_remaining = 125000 - 80000 = 45000.
    taxable_ltcg = 70000 - 45000 = 25000 -> ltcg_tax = 3125.
    stcg_tax = 10000 * 0.20 = 2000.
    """
    gains = [
        FakeGain(gain_type="LTCG", profit_loss=Decimal("80000")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("30000")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-20000")),
        FakeGain(gain_type="LTCG", profit_loss=Decimal("-10000")),
    ]
    service = _service()
    summary = service._compute_fy_summary(gains)

    assert summary["total_ltcg_booked"] == 80000
    assert summary["total_stcg_booked"] == 30000
    assert summary["total_stcg_losses"] == 20000
    assert summary["total_ltcg_losses"] == 10000
    assert summary["ltcg_exemption_remaining"] == 45000
    assert summary["net_stcg"] == 10000
    assert summary["net_ltcg"] == 70000
    assert abs(summary["current_stcg_tax"] - 2000) < 0.01
    assert abs(summary["current_ltcg_tax"] - 3125) < 0.01


def test_ltcg_exemption_harvest_returns_none_when_exhausted():
    """LTCG gains = 130000 exceeds the 125000 limit -> exemption = 0."""
    service = _service()
    fy_summary = service._compute_fy_summary(
        [FakeGain(gain_type="LTCG", profit_loss=Decimal("130000"))]
    )
    assert fy_summary["ltcg_exemption_remaining"] == 0

    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime.now() - timedelta(days=400),
            instrument=FakeInstrument(symbol="RELIANCE"),
        ),
        FakeLot(
            quantity_remaining=Decimal("5"),
            buy_price=Decimal("200"),
            buy_date=datetime.now() - timedelta(days=500),
            instrument=FakeInstrument(symbol="TCS"),
        ),
    ]
    service = _service(lots=lots)
    result = service.strategy_ltcg_exemption_harvest(uuid4(), fy_summary)
    assert result is None


def test_ltcg_exemption_harvest_returns_strategy_when_available():
    """LTCG gains = 50000 -> exemption_remaining = 75000; one lot held 400 days qualifies."""
    service = _service()
    fy_summary = service._compute_fy_summary(
        [FakeGain(gain_type="LTCG", profit_loss=Decimal("50000"))]
    )

    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime.now() - timedelta(days=400),
            instrument=FakeInstrument(symbol="RELIANCE"),
        ),
    ]
    service = _service(lots=lots)
    result = service.strategy_ltcg_exemption_harvest(uuid4(), fy_summary)

    assert result is not None
    assert result["exemption_remaining"] == 75000
    assert len(result["applicable_lots"]) == 1
    assert result["applicable_lots"][0]["qualifies_for_ltcg"] is True


def test_holding_period_optimizer_finds_lot_near_threshold():
    """Lot held 340 days -> 25 days from LTCG (365) -> MEDIUM priority."""
    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime.now() - timedelta(days=340),
            instrument=FakeInstrument(symbol="TCS"),
        ),
    ]
    service = _service(lots=lots)
    alerts = service.strategy_holding_period_optimizer(uuid4())

    assert len(alerts) == 1
    assert alerts[0]["days_to_ltcg"] == 25
    assert alerts[0]["priority"] == "MEDIUM"


def test_holding_period_optimizer_high_priority_under_14_days():
    """Lot held 358 days -> 7 days from LTCG -> HIGH priority, urgent."""
    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime.now() - timedelta(days=358),
            instrument=FakeInstrument(symbol="INFY"),
        ),
    ]
    service = _service(lots=lots)
    alerts = service.strategy_holding_period_optimizer(uuid4())

    assert len(alerts) == 1
    assert alerts[0]["priority"] == "HIGH"
    assert alerts[0]["urgent"] is True


def test_loss_carry_forward_returns_none_when_no_net_loss():
    service = _service()
    fy_summary = service._compute_fy_summary(
        [
            FakeGain(gain_type="LTCG", profit_loss=Decimal("100000")),
            FakeGain(gain_type="LTCG", profit_loss=Decimal("-20000")),
        ]
    )
    result = service.strategy_loss_carry_forward(uuid4(), fy_summary)
    assert result is None


def test_compute_all_strategies_returns_valid_structure():
    # sell_date must fall inside the *current* FY window, which is now
    # computed dynamically from today's date rather than hardcoded -- so
    # "today" is always inside it, unlike a fixed literal date would be
    # once the calendar rolls past that FY.
    gains = [
        FakeGain(
            gain_type="LTCG",
            profit_loss=Decimal("50000"),
            sell_date=datetime.now(),
        ),
    ]
    lots = [
        FakeLot(
            quantity_remaining=Decimal("10"),
            buy_price=Decimal("100"),
            buy_date=datetime.now() - timedelta(days=350),
            instrument=FakeInstrument(symbol="HDFC"),
        ),
    ]
    service = _service(gains=gains, lots=lots)
    result = service.compute_all_strategies(uuid4())

    assert "fy_summary" in result
    assert isinstance(result["strategies"], list)
    assert len(result["strategies"]) >= 1

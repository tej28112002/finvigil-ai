"""
Unit tests for BacktestService.run_backtest. No DB, no network — uses the
FakeGain / FakeRealizedGainRepository fakes from tests/fakes.py plus a
plain SimpleNamespace standing in for BacktestStrategy/BacktestLeg (only
.legs / .start_date / .end_date and leg.segment are ever read).
"""
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.backtest_service import BacktestService
from tests.fakes import FakeGain, FakeRealizedGainRepository


def _strategy(legs, start_date, end_date):
    return SimpleNamespace(legs=legs, start_date=start_date, end_date=end_date)


def _service(gains: list[FakeGain]) -> BacktestService:
    return BacktestService(
        backtest_repository=None,
        realized_gain_repository=FakeRealizedGainRepository(gains),
    )


def test_run_backtest_with_options_leg_returns_insufficient_data():
    strategy = _strategy(
        legs=[SimpleNamespace(segment="options")],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    result = _service([]).run_backtest(strategy, uuid4())

    assert result["status"] == "insufficient_data"
    assert "historical options" in result["message"]


def test_run_backtest_with_no_gains_in_range_returns_insufficient_data():
    strategy = _strategy(
        legs=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    result = _service([]).run_backtest(strategy, uuid4())

    assert result["status"] == "insufficient_data"


def test_run_backtest_with_equity_gains_returns_completed_net_profit():
    """+1000, +500, -200 -> net_profit = 1300.0, total_trades = 3."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("1000"), sell_date=datetime(2024, 3, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("500"), sell_date=datetime(2024, 3, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200"), sell_date=datetime(2024, 3, 3)),
    ]
    strategy = _strategy(
        legs=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    result = _service(gains).run_backtest(strategy, uuid4())

    assert result["status"] == "completed"
    assert result["summary"]["net_profit"] == 1300.0
    assert result["summary"]["total_trades"] == 3

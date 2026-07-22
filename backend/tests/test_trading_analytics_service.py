"""
Unit tests for TradingAnalyticsService. No DB, no network — uses the
FakeGain / FakeRealizedGainRepository fakes from tests/fakes.py.

Expected values are hand-computed from the method's own documented
formulas (this is the project's own analytics design, not external law),
not derived by running the code under test.
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.services.trading_analytics_service import TradingAnalyticsService
from tests.fakes import FakeGain, FakeRealizedGainRepository


def _service(gains: list[FakeGain]) -> TradingAnalyticsService:
    return TradingAnalyticsService(
        realized_gain_repository=FakeRealizedGainRepository(gains),
        trade_repository=None,
        holding_lot_repository=None,
        dashboard_repository=None,
    )


def test_compute_profitability_with_known_wins_and_losses():
    """
    [+500, +300, -200, -100]
    net_profit = 500, gross_profit = 800, gross_loss = -300
    profit_factor = 800/300 ~= 2.667
    win_rate = 2/4 = 0.5, avg_win = 400, avg_loss = -150
    expectancy = 0.5*400 + 0.5*(-150) = 125.0
    """
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("500"), sell_date=datetime(2024, 1, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("300"), sell_date=datetime(2024, 1, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200"), sell_date=datetime(2024, 1, 3)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-100"), sell_date=datetime(2024, 1, 4)),
    ]
    result = _service(gains).compute_profitability(uuid4())

    assert result is not None
    assert abs(result["net_profit"] - 500.0) < 0.01
    assert abs(result["profit_factor"] - (800 / 300)) < 0.001
    assert abs(result["expectancy"] - 125.0) < 0.01


def test_compute_win_loss_three_wins_one_loss():
    """
    [+100, +200, +150, -50]
    win_rate_pct = 3/4 * 100 = 75.0
    avg_win = 150, avg_loss = -50, payoff_ratio = 150/50 = 3.0
    """
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("100"), sell_date=datetime(2024, 1, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("200"), sell_date=datetime(2024, 1, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("150"), sell_date=datetime(2024, 1, 3)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-50"), sell_date=datetime(2024, 1, 4)),
    ]
    result = _service(gains).compute_win_loss(uuid4())

    assert result is not None
    assert abs(result["win_rate_pct"] - 75.0) < 0.01
    assert abs(result["payoff_ratio"] - 3.0) < 0.01


def test_compute_equity_curve_from_three_days():
    """Day 1: +500, Day 2: -200, Day 3: +300 -> cumulative [500, 300, 600]."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("500"), sell_date=datetime(2024, 1, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200"), sell_date=datetime(2024, 1, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("300"), sell_date=datetime(2024, 1, 3)),
    ]
    result = _service(gains).compute_equity_curve(uuid4())

    assert result is not None
    cumulative = [row["cumulative_pnl"] for row in result]
    assert cumulative == [500.0, 300.0, 600.0]


def test_compute_risk_metrics_max_drawdown():
    """
    Daily P&L [0, 1000, -200, 400, -300] -> equity curve [0, 1000, 800, 1200, 900].
    Peak 1200 to 900 = 25% max drawdown.
    """
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("0"), sell_date=datetime(2024, 1, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("1000"), sell_date=datetime(2024, 1, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200"), sell_date=datetime(2024, 1, 3)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("400"), sell_date=datetime(2024, 1, 4)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-300"), sell_date=datetime(2024, 1, 5)),
    ]
    result = _service(gains).compute_risk_metrics(uuid4())

    assert result is not None
    assert abs(result["max_drawdown_pct"] - 25.0) < 0.01


def test_compute_efficiency_pct_profitable_days():
    """Day 1: +300 (profitable), Day 2: -100 (loss), Day 3: +200 (profitable)
    -> pct_profitable_days = 2/3 * 100 ~= 66.67."""
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("300"), sell_date=datetime(2024, 1, 1)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-100"), sell_date=datetime(2024, 1, 2)),
        FakeGain(gain_type="STCG", profit_loss=Decimal("200"), sell_date=datetime(2024, 1, 3)),
    ]
    result = _service(gains).compute_efficiency(uuid4())

    assert result is not None
    assert abs(result["pct_profitable_days"] - 66.67) < 0.01

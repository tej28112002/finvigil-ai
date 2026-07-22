"""
Simplified strategy-backtest simulation.

This is deliberately NOT a real options pricing engine. Any strategy with
an options leg is honestly reported as "insufficient_data" pending real
F&O historical price data. For pure equity/futures strategies (i.e. no
options legs), it replays the user's own realized_gains within the
strategy's date range using the same profitability/risk formulas as
TradingAnalyticsService.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.backtest import BacktestStrategy
from app.repositories.backtest_repository import BacktestRepository
from app.repositories.realized_gain_repository import RealizedGainRepository

_OPTIONS_PENDING_MESSAGE = (
    "F&O strategy backtesting requires historical options price data. "
    "This integration is coming soon. Your strategy has been saved."
)
_NO_GAINS_MESSAGE = (
    "No realized gains found in this date range to simulate against. "
    "Trade more, or widen the date range, and try again."
)
_EQUITY_SIMULATION_NOTE = (
    "Simulation based on your realized equity gains in this date range. "
    "Strategy parameters (entry time, legs, SL/target) will apply once "
    "F&O historical data is integrated."
)


class BacktestService:
    def __init__(
        self,
        backtest_repository: BacktestRepository,
        realized_gain_repository: RealizedGainRepository,
    ):
        self.backtest_repo = backtest_repository
        self.realized_gain_repo = realized_gain_repository

    def run_backtest(self, strategy: BacktestStrategy, user_id: UUID) -> dict:
        legs = list(strategy.legs)

        # STEP 1: any options leg -> honest "coming soon", not a fake result.
        if any(leg.segment == "options" for leg in legs):
            return {
                "status": "insufficient_data",
                "message": _OPTIONS_PENDING_MESSAGE,
                "strategy_type": "options",
                "legs_count": len(legs),
            }

        # STEP 2: equity/futures simulation from realized_gains in range.
        gains = self.realized_gain_repo.get_by_user(user_id)
        start, end = strategy.start_date, strategy.end_date
        in_range = [g for g in gains if start <= g.sell_date.date() <= end]

        if not in_range:
            return {
                "status": "insufficient_data",
                "message": _NO_GAINS_MESSAGE,
                "strategy_type": "equity_simulation",
                "legs_count": len(legs),
            }

        profit_losses = [Decimal(str(g.profit_loss)) for g in in_range]
        net_profit = sum(profit_losses)

        winners = [p for p in profit_losses if p > 0]
        losers = [p for p in profit_losses if p < 0]
        gross_profit = sum(winners) if winners else Decimal("0")
        gross_loss = sum(losers) if losers else Decimal("0")

        profit_factor = (
            float(gross_profit / abs(gross_loss)) if gross_loss != 0 else None
        )
        win_rate = len(winners) / len(profit_losses) if profit_losses else 0.0
        loss_rate = 1 - win_rate
        avg_win = float(sum(winners) / len(winners)) if winners else 0.0
        avg_loss = float(sum(losers) / len(losers)) if losers else 0.0
        # avg_loss is already negative so this is correct
        expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)

        # Daily P&L series + equity curve — same grouping TradingAnalyticsService uses.
        daily_pnl: dict[date, Decimal] = {}
        for g in in_range:
            day = g.sell_date.date()
            daily_pnl[day] = daily_pnl.get(day, Decimal("0")) + Decimal(str(g.profit_loss))
        daily_pnl = dict(sorted(daily_pnl.items()))

        cumulative = Decimal("0")
        curve_raw: list[tuple[date, Decimal]] = []
        for day, pnl in daily_pnl.items():
            cumulative += pnl
            curve_raw.append((day, cumulative))

        daily_values = [float(v) for _, v in curve_raw]
        peak = daily_values[0]
        max_drawdown = 0.0
        for val in daily_values:
            if val > peak:
                peak = val
            if peak != 0:
                dd = (peak - val) / abs(peak) * 100
                if dd > max_drawdown:
                    max_drawdown = dd

        sharpe = None
        if len(daily_pnl) >= 2:
            import numpy as np

            daily_pnl_values = [float(v) for v in daily_pnl.values()]
            mean_daily = float(np.mean(daily_pnl_values))
            std_daily = float(np.std(daily_pnl_values))
            if std_daily > 0:
                sharpe = float((mean_daily / std_daily) * np.sqrt(252))

        equity_curve = [
            {
                "date": str(day),
                "cumulative_pnl": float(val),
                "daily_pnl": float(daily_pnl[day]),
            }
            for day, val in curve_raw
        ]

        return {
            "status": "completed",
            "strategy_type": "equity_simulation",
            "date_range": {"start": str(start), "end": str(end)},
            "summary": {
                "net_profit": float(net_profit),
                "win_rate_pct": float(win_rate * 100),
                "profit_factor": profit_factor,
                "expectancy": expectancy,
                "max_drawdown_pct": max_drawdown,
                "sharpe_ratio": sharpe,
                "total_trades": len(in_range),
                "total_days": len(daily_pnl),
            },
            "equity_curve": equity_curve,
            "note": _EQUITY_SIMULATION_NOTE,
        }

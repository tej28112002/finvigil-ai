"""
Simplified strategy-backtest simulation.

This is deliberately NOT a real options pricing engine. Any strategy with
an options leg is honestly reported as "insufficient_data" pending real
F&O historical price data. For pure equity/futures strategies (i.e. no
options legs), it replays the user's own realized_gains within the
strategy's date range using the same profitability/risk formulas as
TradingAnalyticsService, expanded into an AlgoTest-style report.
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

_MONTH_KEYS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]


def _gain_symbol(g) -> str:
    """RealizedGain has no symbol column of its own; read it through the
    (eager-loaded) instrument relationship when present, else fall back to a
    short slice of the instrument UUID so the report row is never blank."""
    instrument = getattr(g, "instrument", None)
    if instrument is not None and getattr(instrument, "symbol", None):
        return instrument.symbol
    return str(getattr(g, "instrument_id", "") or "")[:8] or "—"


def _max_drawdown_from_curve(
    curve: list[tuple[date, Decimal]],
) -> tuple[float, float, int, str | None, str | None]:
    """Returns (max_dd_rupees, max_dd_pct, duration_days, start_date_str,
    end_date_str) for the largest peak-to-trough drop in a cumulative-P&L
    curve. Drawdown magnitudes are reported as positive numbers."""
    if not curve:
        return 0.0, 0.0, 0, None, None

    peak_val = float(curve[0][1])
    peak_date = curve[0][0]
    max_dd = 0.0
    max_dd_pct = 0.0
    dd_start: date | None = None
    dd_end: date | None = None

    for day, cum in curve:
        val = float(cum)
        if val > peak_val:
            peak_val = val
            peak_date = day
        drop = peak_val - val
        if drop > max_dd:
            max_dd = drop
            max_dd_pct = (drop / abs(peak_val) * 100) if peak_val != 0 else 0.0
            dd_start = peak_date
            dd_end = day

    duration = (dd_end - dd_start).days if dd_start and dd_end else 0
    return (
        max_dd,
        max_dd_pct,
        duration,
        str(dd_start) if dd_start else None,
        str(dd_end) if dd_end else None,
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

        # Sort trades chronologically by sell_date — streaks, curve, and the
        # report table all depend on this order.
        trades_sorted = sorted(in_range, key=lambda g: g.sell_date)
        profit_losses = [Decimal(str(g.profit_loss)) for g in trades_sorted]
        net_profit = sum(profit_losses)

        winners = [p for p in profit_losses if p > 0]
        losers = [p for p in profit_losses if p < 0]

        total_trades = len(profit_losses)
        win_count = len(winners)
        loss_count = len(losers)
        win_pct = float(win_count / total_trades * 100) if total_trades else 0.0
        loss_pct = 100.0 - win_pct

        avg_win = float(sum(winners) / len(winners)) if winners else 0.0
        avg_loss = float(sum(losers) / len(losers)) if losers else 0.0  # negative
        avg_profit_per_trade = float(net_profit / total_trades) if total_trades else 0.0

        max_profit_single = float(max(profit_losses)) if profit_losses else 0.0
        max_loss_single = float(min(profit_losses)) if profit_losses else 0.0

        expectancy_ratio = (win_pct / 100 * avg_win) + (loss_pct / 100 * avg_loss)
        reward_to_risk = float(avg_win / abs(avg_loss)) if avg_loss != 0 else None

        # ── daily P&L series + equity curve with drawdown column ──
        daily_pnl: dict[date, Decimal] = {}
        for g in trades_sorted:
            day = g.sell_date.date()
            daily_pnl[day] = daily_pnl.get(day, Decimal("0")) + Decimal(str(g.profit_loss))
        daily_pnl = dict(sorted(daily_pnl.items()))

        cumulative = Decimal("0")
        curve_raw: list[tuple[date, Decimal]] = []
        for day, pnl in daily_pnl.items():
            cumulative += pnl
            curve_raw.append((day, cumulative))

        peak_so_far = float("-inf")
        equity_curve: list[dict] = []
        for day, cum in curve_raw:
            val = float(cum)
            peak_so_far = max(peak_so_far, val)
            equity_curve.append(
                {
                    "date": str(day),
                    "cumulative_pnl": val,
                    "daily_pnl": float(daily_pnl[day]),
                    "drawdown": val - peak_so_far,  # <= 0
                }
            )

        max_dd_rupees, max_dd_pct, dd_days, dd_start, dd_end = _max_drawdown_from_curve(
            curve_raw
        )
        return_over_max_dd = (
            float(net_profit) / abs(max_dd_rupees) if max_dd_rupees > 0 else None
        )

        # ── max win / losing streaks (by trade, chronological) ──
        win_streak = lose_streak = max_win_streak = max_lose_streak = 0
        for p in profit_losses:
            if p > 0:
                win_streak += 1
                lose_streak = 0
            elif p < 0:
                lose_streak += 1
                win_streak = 0
            else:
                win_streak = lose_streak = 0
            max_win_streak = max(max_win_streak, win_streak)
            max_lose_streak = max(max_lose_streak, lose_streak)

        # ── Sharpe from daily P&L ──
        sharpe = None
        if len(daily_pnl) >= 2:
            import numpy as np

            daily_pnl_values = [float(v) for v in daily_pnl.values()]
            mean_daily = float(np.mean(daily_pnl_values))
            std_daily = float(np.std(daily_pnl_values))
            if std_daily > 0:
                sharpe = float((mean_daily / std_daily) * np.sqrt(252))

        # ── yearly returns (month grid + per-year drawdown) ──
        yearly_returns = self._build_yearly_returns(daily_pnl, curve_raw)

        # ── full report trade rows ──
        trades = [
            {
                "index": i,
                "entry_date": str(g.buy_date.date()) if g.buy_date else None,
                "exit_date": str(g.sell_date.date()),
                "symbol": _gain_symbol(g),
                "gain_type": g.gain_type,
                "quantity": float(g.quantity_sold),
                "entry_price": float(g.buy_price),
                "exit_price": float(g.sell_price),
                "holding_days": g.holding_days,
                "pnl": float(g.profit_loss),
            }
            for i, g in enumerate(trades_sorted, start=1)
        ]

        return {
            "status": "completed",
            "strategy_type": "equity_simulation",
            "date_range": {"start": str(start), "end": str(end)},
            "summary": {
                "overall_profit": float(net_profit),
                "total_trades": total_trades,
                "avg_profit_per_trade": avg_profit_per_trade,
                "win_pct": win_pct,
                "loss_pct": loss_pct,
                "avg_profit_on_winning": avg_win,
                "avg_loss_on_losing": avg_loss,
                "max_profit_single_trade": max_profit_single,
                "max_loss_single_trade": max_loss_single,
                "max_drawdown": max_dd_rupees,
                "max_drawdown_pct": max_dd_pct,
                "max_drawdown_duration_days": dd_days,
                "max_drawdown_start": dd_start,
                "max_drawdown_end": dd_end,
                "return_over_max_dd": return_over_max_dd,
                "reward_to_risk_ratio": reward_to_risk,
                "expectancy_ratio": expectancy_ratio,
                "max_win_streak": max_win_streak,
                "max_losing_streak": max_lose_streak,
                "sharpe_ratio": sharpe,
            },
            "yearly_returns": yearly_returns,
            "equity_curve": equity_curve,
            "trades": trades,
            "note": _EQUITY_SIMULATION_NOTE,
        }

    def _build_yearly_returns(
        self,
        daily_pnl: dict[date, Decimal],
        curve_raw: list[tuple[date, Decimal]],
    ) -> list[dict]:
        """One row per year: each calendar month's P&L (null if no trades
        that month), the year total, and the largest intra-year drawdown
        computed from that year's own cumulative-P&L curve."""
        years = sorted({day.year for day in daily_pnl})
        rows: list[dict] = []

        for year in years:
            month_totals: dict[int, Decimal] = {}
            for day, pnl in daily_pnl.items():
                if day.year == year:
                    month_totals[day.month] = month_totals.get(day.month, Decimal("0")) + pnl

            row: dict = {"year": year}
            for month_idx, key in enumerate(_MONTH_KEYS, start=1):
                row[key] = float(month_totals[month_idx]) if month_idx in month_totals else None
            row["total"] = float(sum(month_totals.values()))

            year_curve = [(d, c) for d, c in curve_raw if d.year == year]
            year_dd, _pct, year_dd_days, _s, _e = _max_drawdown_from_curve(year_curve)
            row["max_drawdown"] = year_dd
            row["days_for_mdd"] = year_dd_days if year_dd > 0 else None
            row["return_over_mdd"] = (
                row["total"] / abs(year_dd) if year_dd > 0 else None
            )
            rows.append(row)

        return rows

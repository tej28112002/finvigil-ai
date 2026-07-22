"""
Trading performance analytics for the /journal page.

Everything here is computed from RealizedGain and Trade records already in
the DB — no external API calls, no yfinance, no Redis.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.realized_gain import RealizedGain
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_repository import TradeRepository


class TradingAnalyticsService:
    def __init__(
        self,
        realized_gain_repository: RealizedGainRepository,
        trade_repository: TradeRepository,
        holding_lot_repository: HoldingLotRepository,
        dashboard_repository: DashboardRepository,
    ):
        self.realized_gain_repo = realized_gain_repository
        self.trade_repo = trade_repository
        self.holding_lot_repo = holding_lot_repository
        self.dashboard_repo = dashboard_repository

    # ── core data builders ──────────────────────────────────────────────

    def _get_realized_gains(self, user_id: UUID) -> list[RealizedGain]:
        return self.realized_gain_repo.get_by_user(user_id)

    def _get_daily_pnl_series(
        self, gains: list[RealizedGain]
    ) -> dict[date, Decimal]:
        """Group gains by sell_date.date() and sum profit_loss per day.
        Returns {date: daily_pnl} sorted by date ascending."""
        daily: dict[date, Decimal] = {}
        for g in gains:
            day = g.sell_date.date()
            daily[day] = daily.get(day, Decimal("0")) + Decimal(str(g.profit_loss))
        return dict(sorted(daily.items()))

    def _get_equity_curve(
        self, daily_pnl: dict[date, Decimal]
    ) -> list[tuple[date, Decimal]]:
        """Running cumulative sum of daily P&L, ascending by date."""
        cumulative = Decimal("0")
        curve: list[tuple[date, Decimal]] = []
        for day, pnl in daily_pnl.items():
            cumulative += pnl
            curve.append((day, cumulative))
        return curve

    # ── section 1: profitability ────────────────────────────────────────

    def compute_profitability(self, user_id: UUID) -> dict | None:
        gains = self._get_realized_gains(user_id)
        if not gains:
            return None

        profit_losses = [Decimal(str(g.profit_loss)) for g in gains]

        net_profit = sum(profit_losses)

        gross_profit = sum(p for p in profit_losses if p > 0)
        gross_loss = sum(p for p in profit_losses if p < 0)

        profit_factor = None
        if gross_loss != 0:
            profit_factor = float(gross_profit / abs(gross_loss))

        winners = [p for p in profit_losses if p > 0]
        losers = [p for p in profit_losses if p < 0]

        win_rate = len(winners) / len(profit_losses) if profit_losses else 0
        loss_rate = 1 - win_rate
        avg_win = float(sum(winners) / len(winners)) if winners else 0
        avg_loss = float(sum(losers) / len(losers)) if losers else 0

        # avg_loss is already negative so this is correct
        expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)

        avg_trade_return = float(net_profit / len(profit_losses))

        daily_pnl = self._get_daily_pnl_series(gains)
        avg_daily_pnl = (
            float(sum(daily_pnl.values()) / len(daily_pnl)) if daily_pnl else None
        )

        return {
            "net_profit": float(net_profit),
            "avg_daily_pnl": avg_daily_pnl,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "avg_trade_return": avg_trade_return,
            "total_return_pct": None,  # filled separately
        }

    # ── section 2: win / loss ───────────────────────────────────────────

    def compute_win_loss(self, user_id: UUID) -> dict | None:
        gains = self._get_realized_gains(user_id)
        if not gains:
            return None

        profit_losses = [Decimal(str(g.profit_loss)) for g in gains]
        winners = [p for p in profit_losses if p > 0]
        losers = [p for p in profit_losses if p < 0]

        win_rate_pct = (
            float(len(winners) / len(profit_losses) * 100) if profit_losses else None
        )
        avg_win = float(sum(winners) / len(winners)) if winners else None
        avg_loss = float(sum(losers) / len(losers)) if losers else None

        payoff_ratio = None
        if avg_win is not None and avg_loss is not None and avg_loss != 0:
            payoff_ratio = float(avg_win / abs(avg_loss))

        largest_win = float(max(profit_losses)) if profit_losses else None
        largest_loss = float(min(profit_losses)) if profit_losses else None

        total_trades = len(profit_losses)
        win_count = len(winners)
        loss_count = len(losers)

        return {
            "win_rate_pct": win_rate_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "payoff_ratio": payoff_ratio,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
        }

    # ── section 3: risk management ──────────────────────────────────────

    def compute_risk_metrics(self, user_id: UUID) -> dict | None:
        gains = self._get_realized_gains(user_id)
        if not gains:
            return None

        daily_pnl = self._get_daily_pnl_series(gains)
        if len(daily_pnl) < 2:
            return None

        equity_curve = self._get_equity_curve(daily_pnl)
        daily_values = [float(v) for _, v in equity_curve]

        # Maximum Drawdown from equity curve
        peak = daily_values[0]
        max_drawdown = 0.0
        for val in daily_values:
            if val > peak:
                peak = val
            if peak != 0:
                dd = (peak - val) / abs(peak) * 100
                if dd > max_drawdown:
                    max_drawdown = dd

        # Volatility — std dev of daily P&L
        daily_pnl_values = [float(v) for v in daily_pnl.values()]
        import numpy as np

        volatility = float(np.std(daily_pnl_values))
        annualized_vol = float(np.std(daily_pnl_values) * np.sqrt(252))

        # Sharpe Ratio using daily P&L: (mean_daily / std_daily) * sqrt(252)
        mean_daily = float(np.mean(daily_pnl_values))
        std_daily = float(np.std(daily_pnl_values))
        sharpe = None
        if std_daily > 0:
            sharpe = float((mean_daily / std_daily) * np.sqrt(252))

        # Sortino Ratio — only downside deviation
        downside = [v for v in daily_pnl_values if v < 0]
        sortino = None
        if len(downside) >= 2:
            downside_std = float(np.std(downside))
            if downside_std > 0:
                sortino = float((mean_daily / downside_std) * np.sqrt(252))

        return {
            "max_drawdown_pct": max_drawdown,
            "daily_pnl_volatility": volatility,
            "annualized_volatility": annualized_vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            # Risk per trade and daily limit cannot be computed without a
            # defined capital base — return null
            "risk_per_trade_pct": None,
            "daily_loss_limit_pct": None,
        }

    # ── section 4: efficiency & consistency ─────────────────────────────

    def compute_efficiency(self, user_id: UUID) -> dict | None:
        gains = self._get_realized_gains(user_id)
        if not gains:
            return None

        total_trades = len(gains)

        daily_pnl = self._get_daily_pnl_series(gains)
        total_trading_days = len(daily_pnl)
        profitable_days = sum(1 for v in daily_pnl.values() if v > 0)
        pct_profitable_days = (
            float(profitable_days / total_trading_days * 100)
            if total_trading_days > 0
            else None
        )

        holding_days = [g.holding_days for g in gains]
        avg_holding_days = (
            float(sum(holding_days) / len(holding_days)) if holding_days else None
        )

        trades_per_day = (
            float(total_trades / total_trading_days)
            if total_trading_days > 0
            else None
        )

        # Recovery Factor = Net Profit / Max Drawdown (₹ amount)
        equity_curve = self._get_equity_curve(daily_pnl)
        equity_values = [float(v) for _, v in equity_curve]
        peak = equity_values[0]
        max_dd_rupees = 0.0
        for val in equity_values:
            if val > peak:
                peak = val
            dd = peak - val
            if dd > max_dd_rupees:
                max_dd_rupees = dd

        net_profit = float(sum(Decimal(str(g.profit_loss)) for g in gains))
        recovery_factor = None
        if max_dd_rupees > 0:
            recovery_factor = float(net_profit / max_dd_rupees)

        return {
            "total_trades": total_trades,
            "trades_per_day_avg": trades_per_day,
            "avg_holding_days": avg_holding_days,
            "total_trading_days": total_trading_days,
            "profitable_days": profitable_days,
            "pct_profitable_days": pct_profitable_days,
            "recovery_factor": recovery_factor,
        }

    # ── section 5: cost & execution ─────────────────────────────────────

    def compute_cost_execution(self, user_id: UUID) -> dict | None:
        # These require the charges table to be populated.
        # Return placeholders with null values and an explanation.
        return {
            "total_charges": None,
            "avg_charge_per_trade": None,
            "breakeven_win_rate_pct": None,
            "slippage_avg": None,
            "turnover_ratio": None,
            "note": "Connect broker and sync trades to see cost metrics",
        }

    # ── section 6: equity curve data ────────────────────────────────────

    def compute_equity_curve(self, user_id: UUID) -> list[dict] | None:
        """Daily cumulative P&L for chart rendering:
        [{"date": "2024-01-15", "cumulative_pnl": 2000.0}, ...]"""
        gains = self._get_realized_gains(user_id)
        if not gains:
            return None

        daily_pnl = self._get_daily_pnl_series(gains)
        if not daily_pnl:
            return None

        equity_curve = self._get_equity_curve(daily_pnl)
        return [
            {
                "date": str(day),
                "cumulative_pnl": float(val),
                "daily_pnl": float(daily_pnl[day]),
            }
            for day, val in equity_curve
        ]

    # ── combined ─────────────────────────────────────────────────────────

    def compute_all(self, user_id: UUID) -> dict:
        """Runs all sections. Each wrapped in try/except returning None."""
        result: dict = {}
        for key, method in [
            ("profitability", self.compute_profitability),
            ("win_loss", self.compute_win_loss),
            ("risk", self.compute_risk_metrics),
            ("efficiency", self.compute_efficiency),
            ("cost_execution", self.compute_cost_execution),
            ("equity_curve", self.compute_equity_curve),
        ]:
            try:
                result[key] = method(user_id)
            except Exception as e:
                print(
                    f"[FINVIGIL] analytics {key} failed: {type(e).__name__}: {e}",
                    flush=True,
                )
                result[key] = None
        return result

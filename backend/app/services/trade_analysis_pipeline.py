from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.trade_analysis_repository import TradeAnalysisRepository
from app.repositories.trade_repository import TradeRepository
from app.services.trade_llm_service import TradeLLMService

ZERO = Decimal("0")
MIN_GAINS_FOR_ANALYSIS = 2


class TradeAnalysisPipeline:
    """
    Orchestrates a weekly AI Journaling analysis: pure-Python base metrics
    -> LLM narrative analysis -> persisted TradeAnalysisResult row. Also
    drives the week-over-week comparison pass. Called both from the
    explicit POST /journal/analyze endpoint and auto-triggered (best-effort,
    exceptions swallowed by the caller) after a broker sync or tradebook
    upload.
    """

    def __init__(
        self,
        trade_repository: TradeRepository,
        realized_gain_repository: RealizedGainRepository,
        trade_analysis_repository: TradeAnalysisRepository,
        trade_llm_service: TradeLLMService,
    ):
        self.trade_repository = trade_repository
        self.realized_gain_repository = realized_gain_repository
        self.trade_analysis_repository = trade_analysis_repository
        self.trade_llm_service = trade_llm_service

    def compute_base_metrics(self, trades: list, gains: list) -> dict:
        profit_losses = [Decimal(str(g.profit_loss)) for g in gains]
        winners = [p for p in profit_losses if p > 0]
        losers = [p for p in profit_losses if p < 0]

        win_rate = (len(winners) / len(profit_losses) * 100) if profit_losses else 0.0
        net_pnl = sum(profit_losses, ZERO)
        gross_profit = sum(winners, ZERO)
        gross_loss = abs(sum(losers, ZERO))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else None

        # Max consecutive losses, walked in chronological order. Gains with
        # no sell_date (shouldn't normally happen) sort last, stable order.
        sorted_gains = sorted(gains, key=lambda g: (g.sell_date is None, g.sell_date))
        max_consecutive_losses = 0
        current_streak = 0
        for g in sorted_gains:
            if Decimal(str(g.profit_loss)) < 0:
                current_streak += 1
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
            else:
                current_streak = 0

        daily_totals: dict = {}
        for g in gains:
            if g.sell_date is None:
                continue
            day = g.sell_date.date()
            daily_totals[day] = daily_totals.get(day, ZERO) + Decimal(str(g.profit_loss))
        worst_day_pnl = min(daily_totals.values()) if daily_totals else ZERO

        instruments = list({str(g.instrument_id) for g in gains})

        return {
            "net_pnl": float(net_pnl),
            "win_rate_pct": float(win_rate),
            "profit_factor": profit_factor,
            "total_trades": len(trades),
            "avg_trade_return": float(net_pnl / len(profit_losses)) if profit_losses else 0.0,
            "gross_profit": float(gross_profit),
            "gross_loss": float(gross_loss),
            "max_consecutive_losses": max_consecutive_losses,
            "worst_day_pnl": float(worst_day_pnl),
            "instruments": instruments,
        }

    def run_weekly_analysis(
        self,
        user_id: UUID,
        week_start: date | None = None,
        week_end: date | None = None,
    ) -> dict:
        if week_end is None:
            week_end = date.today()
        if week_start is None:
            week_start = week_end - timedelta(days=7)

        trades = [
            t
            for t in self.trade_repository.get_by_user(user_id)
            if week_start <= t.execution_time.date() <= week_end
        ]
        gains = [
            g
            for g in self.realized_gain_repository.get_by_user(user_id)
            if g.sell_date and week_start <= g.sell_date.date() <= week_end
        ]

        if len(gains) < MIN_GAINS_FOR_ANALYSIS:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 completed trades to generate analysis.",
                "trade_count": len(trades),
            }

        base_metrics = self.compute_base_metrics(trades, gains)
        analysis_dict, raw = self.trade_llm_service.analyze_trades(
            trades, gains, week_start, week_end, base_metrics
        )

        saved = self.trade_analysis_repository.create_analysis(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            trade_count=len(trades),
            analysis_type="weekly",
            analysis_json=analysis_dict,
            raw_llm_output=raw,
            llm_model=TradeLLMService.GROQ_MODEL,
        )

        return {
            "status": "completed",
            "analysis_id": str(saved.id),
            "week_start": str(week_start),
            "week_end": str(week_end),
            "trade_count": len(trades),
            "analysis": analysis_dict,
        }

    def run_comparison(self, user_id: UUID) -> dict | None:
        latest = self.trade_analysis_repository.get_latest_by_user(user_id)
        if not latest:
            return None
        previous = self.trade_analysis_repository.get_previous_week(
            user_id, latest.week_start
        )
        if not previous:
            return None

        comparison, raw = self.trade_llm_service.compare_analyses(
            previous.analysis_json, latest.analysis_json
        )

        self.trade_analysis_repository.create_analysis(
            user_id=user_id,
            week_start=latest.week_start,
            week_end=latest.week_end,
            trade_count=latest.trade_count,
            analysis_type="comparison",
            analysis_json=comparison,
            raw_llm_output=raw,
            llm_model=TradeLLMService.GROQ_MODEL,
        )

        return {
            "status": "completed",
            "comparison": comparison,
            "current_period": f"{latest.week_start} to {latest.week_end}",
            "previous_period": f"{previous.week_start} to {previous.week_end}",
        }

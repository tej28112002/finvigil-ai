"""
AI Journaling LLM trade analysis (Phase 10 follow-up) --
TradeAnalysisPipeline.compute_base_metrics / run_weekly_analysis.

Pure unit tests via FakeTradeRepository + FakeRealizedGainRepository +
FakeTradeAnalysisRepository (tests/fakes.py) -- no DB, no network.
TradeLLMService is mocked with unittest.mock so no real Groq API call
happens. Expected win-rate/profit-factor values hand-computed independently
from the profit_loss inputs before writing the assertions.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.trade_analysis_pipeline import TradeAnalysisPipeline
from tests.fakes import (
    FakeGain,
    FakeRealizedGainRepository,
    FakeTrade,
    FakeTradeAnalysisRepository,
    FakeTradeRepository,
)

TODAY = date.today()
TODAY_NOON_UTC = datetime.combine(TODAY, datetime.min.time(), tzinfo=timezone.utc)


def make_pipeline(trades=None, gains=None, trade_analysis_repo=None, llm_service=None):
    return TradeAnalysisPipeline(
        trade_repository=FakeTradeRepository(trades or []),
        realized_gain_repository=FakeRealizedGainRepository(gains or []),
        trade_analysis_repository=trade_analysis_repo or FakeTradeAnalysisRepository(),
        trade_llm_service=llm_service or MagicMock(),
    )


def test_compute_base_metrics_known_values():
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("1000")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("500")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-300")),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200")),
    ]
    pipeline = make_pipeline()

    result = pipeline.compute_base_metrics(trades=[], gains=gains)

    assert result["win_rate_pct"] == 50.0
    assert result["net_pnl"] == 1000.0
    assert result["gross_profit"] == 1500.0
    assert result["gross_loss"] == 500.0
    assert result["profit_factor"] == 3.0


def test_run_weekly_analysis_insufficient_data_with_no_gains():
    trade = FakeTrade(idempotency_hash="h1", execution_time=TODAY_NOON_UTC)
    pipeline = make_pipeline(trades=[trade], gains=[])

    result = pipeline.run_weekly_analysis(user_id=uuid4())

    assert result["status"] == "insufficient_data"
    assert result["trade_count"] == 1


def test_run_weekly_analysis_calls_llm_and_saves_result():
    gains = [
        FakeGain(gain_type="STCG", profit_loss=Decimal("1000"), sell_date=TODAY_NOON_UTC),
        FakeGain(gain_type="STCG", profit_loss=Decimal("500"), sell_date=TODAY_NOON_UTC),
        FakeGain(gain_type="STCG", profit_loss=Decimal("-200"), sell_date=TODAY_NOON_UTC),
    ]
    trade_analysis_repo = FakeTradeAnalysisRepository()
    llm_service = MagicMock()
    llm_service.analyze_trades.return_value = ({"grade": "B"}, "raw output")

    pipeline = make_pipeline(
        gains=gains, trade_analysis_repo=trade_analysis_repo, llm_service=llm_service
    )

    result = pipeline.run_weekly_analysis(user_id=uuid4())

    assert llm_service.analyze_trades.call_count == 1
    assert len(trade_analysis_repo.created) == 1
    assert result["status"] == "completed"
    assert result["analysis"]["grade"] == "B"

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.trade_analysis import TradeAnalysisResult
from app.repositories.base import BaseRepository


class TradeAnalysisRepository(BaseRepository[TradeAnalysisResult]):
    def __init__(self, db: Session):
        super().__init__(db, TradeAnalysisResult)

    def create_analysis(
        self,
        user_id: uuid.UUID,
        week_start: date,
        week_end: date,
        trade_count: int,
        analysis_type: str,
        analysis_json: dict,
        raw_llm_output: str | None,
        llm_model: str,
    ) -> TradeAnalysisResult:
        return self.create(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            trade_count=trade_count,
            analysis_type=analysis_type,
            analysis_json=analysis_json,
            raw_llm_output=raw_llm_output,
            llm_model=llm_model,
        )

    def get_latest_by_user(
        self, user_id: uuid.UUID
    ) -> TradeAnalysisResult | None:
        return (
            self.db.query(TradeAnalysisResult)
            .filter(
                TradeAnalysisResult.user_id == user_id,
                TradeAnalysisResult.analysis_type == "weekly",
            )
            .order_by(TradeAnalysisResult.week_start.desc())
            .first()
        )

    def get_by_user(
        self, user_id: uuid.UUID, limit: int = 20
    ) -> list[TradeAnalysisResult]:
        return (
            self.db.query(TradeAnalysisResult)
            .filter(TradeAnalysisResult.user_id == user_id)
            .order_by(TradeAnalysisResult.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_previous_week(
        self, user_id: uuid.UUID, before_date: date
    ) -> TradeAnalysisResult | None:
        return (
            self.db.query(TradeAnalysisResult)
            .filter(
                TradeAnalysisResult.user_id == user_id,
                TradeAnalysisResult.analysis_type == "weekly",
                TradeAnalysisResult.week_start < before_date,
            )
            .order_by(TradeAnalysisResult.week_start.desc())
            .first()
        )

    def get_by_id_and_user(
        self, analysis_id: uuid.UUID, user_id: uuid.UUID
    ) -> TradeAnalysisResult | None:
        return (
            self.db.query(TradeAnalysisResult)
            .filter(
                TradeAnalysisResult.id == analysis_id,
                TradeAnalysisResult.user_id == user_id,
            )
            .first()
        )

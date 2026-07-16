import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.harvest_recommendation_line import HarvestRecommendationLine
from app.models.harvest_run import HarvestRun
from app.models.holding_lot import HoldingLot
from app.repositories.base import BaseRepository


class HarvestRunRepository(BaseRepository[HarvestRun]):
    def __init__(self, db: Session):
        super().__init__(db, HarvestRun)

    def create_run(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> HarvestRun:
        return self.create(
            user_id=user_id,
            assessment_year=assessment_year,
            status="processing",
        )

    def add_recommendation_lines(
        self,
        harvest_run_id: uuid.UUID,
        user_id: uuid.UUID,
        candidates: list[dict],
    ) -> None:
        for candidate in candidates:
            line = HarvestRecommendationLine(
                user_id=user_id,
                harvest_run_id=harvest_run_id,
                holding_lot_id=candidate["lot_id"],
                quantity_to_sell=candidate["quantity"],
                simulated_stcg_ltcg=candidate["unrealized_loss"],
                savings_amount=candidate["estimated_tax_saving"],
            )
            self.db.add(line)
        self.db.flush()

    def mark_completed(
        self,
        harvest_run: HarvestRun,
        total_tax_saved_estimate,
    ) -> HarvestRun:
        harvest_run.status = "completed"
        harvest_run.total_tax_saved_estimate = total_tax_saved_estimate
        self.db.flush()
        self.db.refresh(harvest_run)
        return harvest_run

    def mark_failed(self, harvest_run: HarvestRun) -> HarvestRun:
        harvest_run.status = "failed"
        self.db.flush()
        self.db.refresh(harvest_run)
        return harvest_run

    def get_latest_completed(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
        since: datetime,
    ) -> HarvestRun | None:
        """
        Freshness is judged against `since` — the caller passes the most
        recent 06:00 IST boundary (see HarvestCacheService), not a flat
        "N hours old" heuristic, so cache validity stays exactly aligned
        with the daily job's actual schedule.
        """
        return (
            self.db.query(HarvestRun)
            .filter(
                HarvestRun.user_id == user_id,
                HarvestRun.assessment_year == assessment_year,
                HarvestRun.status == "completed",
                HarvestRun.is_deleted.is_(False),
                HarvestRun.created_at >= since,
            )
            .order_by(HarvestRun.created_at.desc())
            .first()
        )

    def get_recommendation_lines(
        self,
        harvest_run_id: uuid.UUID,
    ) -> list[HarvestRecommendationLine]:
        return (
            self.db.query(HarvestRecommendationLine)
            .options(
                joinedload(HarvestRecommendationLine.holding_lot).joinedload(
                    HoldingLot.instrument
                )
            )
            .filter(HarvestRecommendationLine.harvest_run_id == harvest_run_id)
            .all()
        )

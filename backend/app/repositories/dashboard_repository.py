import uuid

from sqlalchemy.orm import Session

from app.models.dashboard_projection import DashboardProjection
from app.repositories.base import BaseRepository


class DashboardRepository(BaseRepository[DashboardProjection]):
    def __init__(self, db: Session):
        super().__init__(db, DashboardProjection)

    def get_by_user(self, user_id: uuid.UUID) -> DashboardProjection | None:
        return (
            self.db.query(DashboardProjection)
            .filter(DashboardProjection.user_id == user_id)
            .first()
        )

    def upsert_projection(
        self,
        user_id: uuid.UUID,
        total_equity_value: float,
        total_crypto_value: float,
        day_pnl: float,
        unrealized_pnl: float,
    ) -> DashboardProjection:
        existing = self.get_by_user(user_id)

        if existing:
            existing.total_equity_value = total_equity_value
            existing.total_crypto_value = total_crypto_value
            existing.day_pnl = day_pnl
            existing.unrealized_pnl = unrealized_pnl
            self.db.flush()
            self.db.refresh(existing)
            return existing

        return self.create(
            user_id=user_id,
            total_equity_value=total_equity_value,
            total_crypto_value=total_crypto_value,
            day_pnl=day_pnl,
            unrealized_pnl=unrealized_pnl,
        )
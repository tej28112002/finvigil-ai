import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.corporate_action_adjustment import CorporateActionAdjustment
from app.repositories.base import BaseRepository


class CorporateActionRepository(BaseRepository[CorporateActionAdjustment]):
    def __init__(self, db: Session):
        super().__init__(db, CorporateActionAdjustment)

    def create_adjustment(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID,
        action_type: str,
        ratio: float,
        applied_at: datetime,
    ) -> CorporateActionAdjustment:
        return self.create(
            user_id=user_id,
            instrument_id=instrument_id,
            action_type=action_type,
            ratio=ratio,
            applied_at=applied_at,
        )

    def get_by_user(
        self,
        user_id: uuid.UUID
    ) -> list[CorporateActionAdjustment]:
        return (
            self.db.query(CorporateActionAdjustment)
            .filter(CorporateActionAdjustment.user_id == user_id)
            .order_by(CorporateActionAdjustment.applied_at.desc())
            .all()
        )

    def get_by_instrument(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID
    ) -> list[CorporateActionAdjustment]:
        return (
            self.db.query(CorporateActionAdjustment)
            .filter(
                CorporateActionAdjustment.user_id == user_id,
                CorporateActionAdjustment.instrument_id == instrument_id,
            )
            .order_by(CorporateActionAdjustment.applied_at.desc())
            .all()
        )

    def get_duplicate(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID,
        action_type: str,
        applied_at: datetime,
    ) -> CorporateActionAdjustment | None:
        return (
            self.db.query(CorporateActionAdjustment)
            .filter(
                CorporateActionAdjustment.user_id == user_id,
                CorporateActionAdjustment.instrument_id == instrument_id,
                CorporateActionAdjustment.action_type == action_type,
                CorporateActionAdjustment.applied_at == applied_at,
            )
            .first()
        )

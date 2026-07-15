import uuid

from sqlalchemy.orm import Session

from app.models.feature_flag import FeatureFlag
from app.repositories.base import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    def __init__(self, db: Session):
        super().__init__(db, FeatureFlag)

    def get_global(self, flag_key: str) -> FeatureFlag | None:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.flag_key == flag_key, FeatureFlag.user_id.is_(None))
            .first()
        )

    def get_user_override(
        self, flag_key: str, user_id: uuid.UUID
    ) -> FeatureFlag | None:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.flag_key == flag_key, FeatureFlag.user_id == user_id)
            .first()
        )

    def get_all(self) -> list[FeatureFlag]:
        return (
            self.db.query(FeatureFlag)
            .order_by(FeatureFlag.flag_key.asc())
            .all()
        )

    def upsert(
        self,
        flag_key: str,
        is_enabled: bool,
        description: str | None,
        user_id: uuid.UUID | None = None,
    ) -> FeatureFlag:
        existing = (
            self.get_user_override(flag_key, user_id)
            if user_id
            else self.get_global(flag_key)
        )
        if existing:
            existing.is_enabled = is_enabled
            if description is not None:
                existing.description = description
            self.db.flush()
            self.db.refresh(existing)
            return existing

        return self.create(
            flag_key=flag_key,
            user_id=user_id,
            is_enabled=is_enabled,
            description=description,
        )

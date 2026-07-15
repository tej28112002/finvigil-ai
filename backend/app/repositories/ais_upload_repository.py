import uuid

from sqlalchemy.orm import Session

from app.models.ais_upload import AisUpload
from app.repositories.base import BaseRepository


class AisUploadRepository(BaseRepository[AisUpload]):
    def __init__(self, db: Session):
        super().__init__(db, AisUpload)

    def create_upload(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
        version: int,
        is_latest: bool,
        raw_json: dict | None,
    ) -> AisUpload:
        return self.create(
            user_id=user_id,
            assessment_year=assessment_year,
            version=version,
            is_latest=is_latest,
            raw_json=raw_json,
        )

    def get_by_id_and_user(
        self,
        upload_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AisUpload | None:
        return (
            self.db.query(AisUpload)
            .filter(
                AisUpload.id == upload_id,
                AisUpload.user_id == user_id,
                AisUpload.is_deleted.is_(False),
            )
            .first()
        )

    def get_by_user_and_ay(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> list[AisUpload]:
        """Full version history for one (user, AY), newest version first."""
        return (
            self.db.query(AisUpload)
            .filter(
                AisUpload.user_id == user_id,
                AisUpload.assessment_year == assessment_year,
                AisUpload.is_deleted.is_(False),
            )
            .order_by(AisUpload.version.desc())
            .all()
        )

    def get_latest_by_user_and_ay(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> AisUpload | None:
        return (
            self.db.query(AisUpload)
            .filter(
                AisUpload.user_id == user_id,
                AisUpload.assessment_year == assessment_year,
                AisUpload.is_latest.is_(True),
                AisUpload.is_deleted.is_(False),
            )
            .first()
        )

    def get_max_version(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> int:
        """
        Next version = this + 1. Includes soft-deleted rows in the max —
        the (user_id, assessment_year, version) DB constraint is unique
        regardless of is_deleted, so a deleted version's number can't be
        reissued.
        """
        latest = (
            self.db.query(AisUpload)
            .filter(
                AisUpload.user_id == user_id,
                AisUpload.assessment_year == assessment_year,
            )
            .order_by(AisUpload.version.desc())
            .first()
        )
        return latest.version if latest else 0

    def clear_latest_flag(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> None:
        """Unsets is_latest on every existing upload for this (user, AY)
        before a new upload takes the flag — keeps exactly one latest."""
        (
            self.db.query(AisUpload)
            .filter(
                AisUpload.user_id == user_id,
                AisUpload.assessment_year == assessment_year,
                AisUpload.is_latest.is_(True),
            )
            .update({AisUpload.is_latest: False}, synchronize_session=False)
        )
        self.db.flush()

    def soft_delete(self, upload: AisUpload) -> None:
        upload.is_deleted = True
        upload.is_latest = False
        self.db.flush()
        self.db.refresh(upload)

    def promote_to_latest(self, upload: AisUpload) -> None:
        upload.is_latest = True
        self.db.flush()
        self.db.refresh(upload)

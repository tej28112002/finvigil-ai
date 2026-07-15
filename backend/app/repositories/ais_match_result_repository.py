import uuid

from sqlalchemy.orm import Session

from app.models.ais_match_result import AisMatchResult
from app.repositories.base import BaseRepository


class AisMatchResultRepository(BaseRepository[AisMatchResult]):
    def __init__(self, db: Session):
        super().__init__(db, AisMatchResult)

    def bulk_create(
        self,
        user_id: uuid.UUID,
        ais_upload_id: uuid.UUID,
        results: list[dict],
    ) -> list[AisMatchResult]:
        """
        results: list of {"ais_line_id": UUID, "match_status": str,
        "mismatch_type": str | None, "resolution_notes": str | None}.
        Same one-flush-per-batch reasoning as AisLineRepository.bulk_create.
        """
        instances = [
            AisMatchResult(
                user_id=user_id,
                ais_upload_id=ais_upload_id,
                ais_line_id=r["ais_line_id"],
                holding_lot_id=r.get("holding_lot_id"),
                match_status=r["match_status"],
                mismatch_type=r.get("mismatch_type"),
                resolution_notes=r.get("resolution_notes"),
            )
            for r in results
        ]
        self.db.add_all(instances)
        self.db.flush()
        for instance in instances:
            self.db.refresh(instance)
        return instances

    def get_by_upload(
        self,
        ais_upload_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[AisMatchResult]:
        return (
            self.db.query(AisMatchResult)
            .filter(
                AisMatchResult.ais_upload_id == ais_upload_id,
                AisMatchResult.user_id == user_id,
            )
            .all()
        )

    def get_mismatches_by_upload(
        self,
        ais_upload_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[AisMatchResult]:
        return (
            self.db.query(AisMatchResult)
            .filter(
                AisMatchResult.ais_upload_id == ais_upload_id,
                AisMatchResult.user_id == user_id,
                AisMatchResult.match_status.in_(["mismatch", "unresolved"]),
            )
            .all()
        )

    def get_by_id_and_user(
        self,
        match_result_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AisMatchResult | None:
        return (
            self.db.query(AisMatchResult)
            .filter(
                AisMatchResult.id == match_result_id,
                AisMatchResult.user_id == user_id,
            )
            .first()
        )

    def update_resolution(
        self,
        match_result: AisMatchResult,
        resolution_notes: str,
    ) -> AisMatchResult:
        match_result.resolution_notes = resolution_notes
        self.db.flush()
        self.db.refresh(match_result)
        return match_result

    def bulk_resolve_exact_matches(
        self,
        ais_upload_id: uuid.UUID,
        user_id: uuid.UUID,
        resolution_notes: str,
    ) -> int:
        """
        Marks every 'matched' row on this upload that hasn't already been
        annotated as reviewed. Returns the count touched — used for the
        "bulk exact-match" action (FR-AIS-04): confirm every already-exact
        row in one action instead of clicking through each one.
        """
        updated = (
            self.db.query(AisMatchResult)
            .filter(
                AisMatchResult.ais_upload_id == ais_upload_id,
                AisMatchResult.user_id == user_id,
                AisMatchResult.match_status == "matched",
                AisMatchResult.resolution_notes.is_(None),
            )
            .update(
                {AisMatchResult.resolution_notes: resolution_notes},
                synchronize_session=False,
            )
        )
        self.db.flush()
        return updated

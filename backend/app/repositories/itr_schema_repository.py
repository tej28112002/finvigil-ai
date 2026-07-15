from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.itr_schema_mapping import ItrSchemaMapping
from app.repositories.base import BaseRepository


class ItrSchemaRepository(BaseRepository[ItrSchemaMapping]):
    def __init__(self, db: Session):
        super().__init__(db, ItrSchemaMapping)

    def get_by_ay(self, ay: str) -> ItrSchemaMapping | None:
        return (
            self.db.query(ItrSchemaMapping)
            .filter(ItrSchemaMapping.ay == ay)
            .first()
        )

    def get_all(self) -> list[ItrSchemaMapping]:
        return (
            self.db.query(ItrSchemaMapping)
            .order_by(ItrSchemaMapping.ay.desc())
            .all()
        )

    def get_all_active(self) -> list[ItrSchemaMapping]:
        return (
            self.db.query(ItrSchemaMapping)
            .filter(ItrSchemaMapping.is_active.is_(True))
            .order_by(ItrSchemaMapping.ay.desc())
            .all()
        )

    def create_or_update(
        self,
        ay: str,
        schema_version: str,
        mapping_json: dict,
    ) -> ItrSchemaMapping:
        """
        Upsert on the (unique) ay column — re-uploading the same AY updates
        its existing row in place (new schema_version/mapping_json, fresh
        uploaded_at) rather than violating the unique constraint.
        """
        existing = self.get_by_ay(ay)
        if existing:
            existing.schema_version = schema_version
            existing.mapping_json = mapping_json
            existing.uploaded_at = datetime.now(timezone.utc)
            self.db.flush()
            self.db.refresh(existing)
            return existing

        return self.create(
            ay=ay,
            schema_version=schema_version,
            mapping_json=mapping_json,
            is_active=True,
        )

    def set_active(self, ay: str, is_active: bool) -> ItrSchemaMapping | None:
        mapping = self.get_by_ay(ay)
        if not mapping:
            return None
        mapping.is_active = is_active
        self.db.flush()
        self.db.refresh(mapping)
        return mapping

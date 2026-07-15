import uuid

from sqlalchemy.orm import Session

from app.models.ais_line import AisLine
from app.repositories.base import BaseRepository


class AisLineRepository(BaseRepository[AisLine]):
    def __init__(self, db: Session):
        super().__init__(db, AisLine)

    def bulk_create(
        self,
        user_id: uuid.UUID,
        ais_upload_id: uuid.UUID,
        lines: list[dict],
    ) -> list[AisLine]:
        """
        lines: list of {"section_code": str, "description": str | None,
        "reported_amount": Decimal | None}. One flush for the whole batch —
        the individual BaseRepository.create() does a flush+refresh per
        row, which would be one round-trip per line on a file that can
        have dozens of entries.
        """
        instances = [
            AisLine(
                user_id=user_id,
                ais_upload_id=ais_upload_id,
                section_code=line["section_code"],
                description=line.get("description"),
                reported_amount=line.get("reported_amount"),
            )
            for line in lines
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
    ) -> list[AisLine]:
        return (
            self.db.query(AisLine)
            .filter(
                AisLine.ais_upload_id == ais_upload_id,
                AisLine.user_id == user_id,
            )
            .order_by(AisLine.section_code.asc())
            .all()
        )

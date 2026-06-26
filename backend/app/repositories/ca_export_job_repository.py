import uuid

from sqlalchemy.orm import Session

from app.models.ca_export_job import CaExportJob
from app.repositories.base import BaseRepository


class CaExportJobRepository(BaseRepository[CaExportJob]):
    def __init__(self, db: Session):
        super().__init__(db, CaExportJob)

    def create_export_job(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
        export_type: str,
        status: str,
    ) -> CaExportJob:
        return self.create(
            user_id=user_id,
            assessment_year=assessment_year,
            export_type=export_type,
            status=status,
        )

    def get_by_user(
        self,
        user_id: uuid.UUID
    ) -> list[CaExportJob]:
        return (
            self.db.query(CaExportJob)
            .filter(CaExportJob.user_id == user_id)
            .order_by(CaExportJob.created_at.desc())
            .all()
        )

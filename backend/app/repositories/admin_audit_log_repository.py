import uuid

from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.repositories.base import BaseRepository


class AdminAuditLogRepository(BaseRepository[AdminAuditLog]):
    def __init__(self, db: Session):
        super().__init__(db, AdminAuditLog)

    def log(
        self,
        admin_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        action: str,
        context: dict | None = None,
    ) -> AdminAuditLog:
        return self.create(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            action=action,
            context=context,
        )

    def get_recent(self, limit: int = 100) -> list[AdminAuditLog]:
        return (
            self.db.query(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

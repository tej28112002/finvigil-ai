import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AdminAuditLog(UUIDMixin, TimestampMixin, Base):
    """
    BRD FR-ADM-02: "full audit" for every admin action — role changes,
    feature-flag edits, and impersonation views/broker-resyncs (this app's
    scoped-down, read-only interpretation of "impersonation"; see
    AdminService for why a full session-swap wasn't built). Table already
    existed in the live schema before Phase 14 — this just maps it.
    """

    __tablename__ = "admin_audit_logs"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

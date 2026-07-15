import uuid

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserTaxPersona(TimestampMixin, Base):
    """
    Per-user tax persona settings (BRD FR-PLT-03) plus role (Phase 14
    RBAC). user_id is the primary key, not a UUIDMixin id — this table is
    a 1:1 extension of auth.users, not an independently-identified entity.

    is_admin is the ORIGINAL boolean flag (pre-Phase-14) — kept, not
    dropped, and backfilled to role='admin' where it was TRUE. `role` is
    now the authoritative field (checked by admin_auth.py); is_admin is no
    longer read by any code path but stays for historical/audit purposes
    rather than a destructive column drop.
    """

    __tablename__ = "user_tax_personas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tax_persona: Mapped[str] = mapped_column(
        ENUM(
            "ITR-3", "ITR-4",
            name="tax_persona_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="ITR-3",
    )
    ay_overrides_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    role: Mapped[str] = mapped_column(
        ENUM(
            "user", "support", "admin",
            name="admin_role_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="user",
    )

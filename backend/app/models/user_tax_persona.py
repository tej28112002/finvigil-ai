import uuid

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserTaxPersona(TimestampMixin, Base):
    """
    Per-user tax persona settings (BRD FR-PLT-03) plus is_admin — a minimal
    role flag added for the ITR schema Admin Panel (no separate roles table
    yet; a real RBAC model is Phase 14). user_id is the primary key, not a
    UUIDMixin id — this table is a 1:1 extension of auth.users, not an
    independently-identified entity.
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

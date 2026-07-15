import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class FeatureFlag(UUIDMixin, TimestampMixin, Base):
    """
    BRD FR-ADM-01: feature flags per user/module. A row with user_id=NULL
    is the GLOBAL default for that flag_key; a row with user_id set is a
    per-user override. The live table enforces "at most one global row per
    flag_key" and "at most one override row per (flag_key, user_id)" via
    two partial unique indexes (NULL isn't equal to NULL under a plain
    UNIQUE constraint, so a partial index was required, not a plain one).
    """

    __tablename__ = "feature_flags"

    flag_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

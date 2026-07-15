import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, UUIDMixin


class AisUpload(UUIDMixin, TimestampMixin, Base):
    """
    One uploaded AIS file for one (user, assessment_year, version).
    A user may re-upload a corrected/updated AIS for the same AY multiple
    times (BRD FR-AIS-02) — each upload gets the next integer version for
    that (user, AY), and is_latest marks the current one. Only is_latest
    uploads are used by the match engine / dashboards; older versions are
    kept for history, never overwritten in place.
    """

    __tablename__ = "ais_uploads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_year: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_latest: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    raw_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    upload_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AisLine(UUIDMixin, TimestampMixin, Base):
    """
    One reported entry within an AisUpload — mirrors how the real income-tax
    AIS/TIS portal reports data: aggregated per SFT source/section, not
    per-transaction (no ISIN/quantity/price at this granularity). The match
    engine (AisMatchingService) reconciles these against FinVigil's own
    computed totals at the same section-category level.
    """

    __tablename__ = "ais_lines"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ais_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ais_uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reported_amount: Mapped[float | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
    )

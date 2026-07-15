import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AisMatchResult(UUIDMixin, TimestampMixin, Base):
    """
    The auto-match engine's verdict for one AisLine: exactly one row per
    line (ais_line_id is NOT NULL), produced by AisMatchingService by
    comparing the line's reported_amount against FinVigil's own computed
    total for that section's category (see AisMatchingService for the
    category-detection + tolerance logic). holding_lot_id stays NULL for
    virtually all rows — ais_lines carries no per-instrument detail (no
    ISIN/symbol), so a specific lot can't be attributed; the column exists
    per the BRD data model for a future per-instrument AIS format.
    """

    __tablename__ = "ais_match_results"

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
    ais_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ais_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("holding_lots.id", ondelete="SET NULL"),
        nullable=True,
    )
    match_status: Mapped[str] = mapped_column(
        ENUM(
            "matched", "mismatch", "unresolved",
            name="ais_match_status_enum",
            create_type=False,
        ),
        nullable=False,
        index=True,
    )
    mismatch_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

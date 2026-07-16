import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class HarvestRun(UUIDMixin, TimestampMixin, Base):
    """
    One harvest-scan snapshot for a user+AY (Phase 12b cache — table
    already existed in db/schema.sql per the BRD §14 data model, deployed
    but never wired to app code until now). Pro/Premium only: the daily
    06:00 IST job and the API's own cache-miss fallback both write rows
    here; Free tier's harvest calls stay pure compute-on-demand via
    HarvestingService directly and never touch this table (FR-HAR-03:
    "Free on-demand only").
    """

    __tablename__ = "harvest_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_year: Mapped[str] = mapped_column(String(9), nullable=False)
    status: Mapped[str] = mapped_column(
        ENUM(
            "pending", "processing", "completed", "failed",
            name="harvest_status_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="pending",
    )
    total_tax_saved_estimate: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        server_default="0",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

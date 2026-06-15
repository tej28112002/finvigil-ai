import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaxSummary(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tax_summaries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_year: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
    )

    total_stcg_gains: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    total_ltcg_gains: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    stcg_tax_rate: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.2000
    )
    ltcg_tax_rate: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.1250
    )
    ltcg_exemption: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=125000
    )
    taxable_stcg: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    taxable_ltcg: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    stcg_tax: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    ltcg_tax: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    total_tax_liability: Mapped[float] = mapped_column(
        Numeric(18, 8), nullable=False, default=0
    )
    calculated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "assessment_year",
            name="uq_tax_summaries_user_year"
        ),
    )

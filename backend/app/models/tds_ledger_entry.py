import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TdsLedgerEntry(UUIDMixin, TimestampMixin, Base):
    """
    A 1% TDS deduction recorded on a crypto/VDA sell. Maps to the existing
    tds_credit_ledger table. TDS is a prepaid credit the taxpayer sets off
    against final VDA tax.
    """

    __tablename__ = "tds_credit_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

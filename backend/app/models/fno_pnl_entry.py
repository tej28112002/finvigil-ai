import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class FnoPnlEntry(UUIDMixin, TimestampMixin, Base):
    """
    One FIFO-matched F&O buy↔sell leg. F&O P&L is business income (PGBP),
    stored separately from realized_gains (equity capital gains). No
    holding-period / STCG-LTCG concept applies.

    Unmatched sells (expired or shorted contracts) are stored with
    buy_trade_id NULL, buy_time NULL, buy_price 0, and
    profit_loss = sell_price × quantity.
    """

    __tablename__ = "fno_pnl_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    buy_trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
    )
    sell_trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    buy_price: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    sell_price: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    buy_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    sell_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    profit_loss: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    is_intraday: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    assessment_year: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
        index=True,
    )

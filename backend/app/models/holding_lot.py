import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.instrument import Instrument
    from app.models.trade import Trade


class HoldingLot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "holding_lots"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        nullable=False,
    )

    broker_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity_bought: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    quantity_remaining: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    buy_price: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    buy_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        ENUM(
            "open", "partial", "closed",
            name="lot_status_enum",
            create_type=False,
        ),
        nullable=False,
        index=True,
    )

    trade: Mapped["Trade"] = relationship(
        back_populates="holding_lots",
    )

    instrument: Mapped["Instrument"] = relationship(
        back_populates="holding_lots",
    )

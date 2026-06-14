import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.broker_connection import BrokerConnection
    from app.models.instrument import Instrument
    from app.models.holding_lot import HoldingLot


class Trade(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint(
            "broker_connection_id", "broker_trade_id",
            name="uq_trades_broker_connection_trade",
        ),
        Index("idx_user_instrument", "user_id", "instrument_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    broker_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("broker_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    broker_trade_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    trade_type: Mapped[str] = mapped_column(
        Enum(
            "buy", "sell",
            name="trade_type_enum",
            create_type=False,
        ),
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    price: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )
    execution_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    idempotency_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    broker_connection: Mapped["BrokerConnection"] = relationship(
        back_populates="trades",
    )

    instrument: Mapped["Instrument"] = relationship(
        back_populates="trades",
    )

    holding_lots: Mapped[list["HoldingLot"]] = relationship(
        "HoldingLot",
        back_populates="trade",
    )
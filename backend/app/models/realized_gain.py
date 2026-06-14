import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RealizedGain(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "realized_gains"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sell_trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("holding_lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_sold: Mapped[float] = mapped_column(
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

    buy_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    sell_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    holding_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    gain_type: Mapped[str] = mapped_column(
        ENUM(
            "STCG", "LTCG",
            name="capital_gain_type_enum",
            create_type=False,
        ),
        nullable=False,
        index=True,
    )

    profit_loss: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

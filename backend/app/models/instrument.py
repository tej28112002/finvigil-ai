from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.trade import Trade
    from app.models.holding_lot import HoldingLot


class Instrument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "instruments"

    isin: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    instrument_type: Mapped[str] = mapped_column(
        "type",
        ENUM(
            "equity", "fno", "mf", "crypto",
            name="instrument_type_enum",
            create_type=False,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    trades: Mapped[List["Trade"]] = relationship(
        "Trade",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )

    holding_lots: Mapped[List["HoldingLot"]] = relationship(
        "HoldingLot",
        back_populates="instrument",
    )
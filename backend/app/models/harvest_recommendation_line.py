import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.holding_lot import HoldingLot


class HarvestRecommendationLine(UUIDMixin, TimestampMixin, Base):
    """
    One harvest-candidate lot within a HarvestRun. Deliberately does NOT
    duplicate symbol/buy_price/buy_date/instrument_id — those are read
    back through holding_lot (FK) at query time instead, so this table
    only stores what a HoldingLot row can't already answer:
    quantity_to_sell (candidate["quantity"]), simulated_stcg_ltcg
    (candidate["unrealized_loss"], signed negative — same convention as
    every other P&L figure in this app), and savings_amount
    (candidate["estimated_tax_saving"]).

    is_price_estimate is never stored because it's always False for any
    row that makes it in here: HarvestingService.get_harvest_candidates
    only ever includes a lot when unrealized_loss < 0, and its own
    cost-basis price-estimate fallback can never itself produce a loss
    (current_price == buy_price -> unrealized_loss == 0) — see that
    method's comment. So every persisted line is backed by a real live
    price at write time, by construction.
    """

    __tablename__ = "harvest_recommendation_lines"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    harvest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("harvest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("holding_lots.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity_to_sell: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    simulated_stcg_ltcg: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    savings_amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    holding_lot: Mapped["HoldingLot"] = relationship()

import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.holding_lot import HoldingLot
from app.repositories.base import BaseRepository


class HoldingLotRepository(BaseRepository[HoldingLot]):
    def __init__(self, db: Session):
        super().__init__(db, HoldingLot)

    def get_open_lots(
        self, user_id: uuid.UUID, instrument_id: uuid.UUID
    ) -> list[HoldingLot]:
        return (
            self.db.query(HoldingLot)
            .filter(
                HoldingLot.user_id == user_id,
                HoldingLot.instrument_id == instrument_id,
                HoldingLot.status.in_(["open", "partial"]),
            )
            .order_by(HoldingLot.buy_date.asc())
            .all()
        )

    def get_open_lots_before_date(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID,
        before_date: datetime,
    ) -> list[HoldingLot]:
        return (
            self.db.query(HoldingLot)
            .filter(
                HoldingLot.user_id == user_id,
                HoldingLot.instrument_id == instrument_id,
                HoldingLot.status.in_(["open", "partial"]),
                HoldingLot.buy_date < before_date,
            )
            .order_by(HoldingLot.buy_date.asc())
            .all()
        )

    def create_lot(
        self,
        user_id: uuid.UUID,
        broker_connection_id: uuid.UUID,
        instrument_id: uuid.UUID,
        source_trade_id: uuid.UUID,
        quantity_bought: float,
        remaining_quantity: float,
        buy_price: float,
        buy_date: datetime,
        status: str,
    ) -> HoldingLot:
        return self.create(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            source_trade_id=source_trade_id,
            quantity_bought=quantity_bought,
            quantity_remaining=remaining_quantity,
            buy_price=buy_price,
            buy_date=buy_date,
            status=status,
        )

    def update_remaining_quantity(
        self, lot: HoldingLot, remaining_quantity: float, status: str
    ) -> HoldingLot:
        lot.quantity_remaining = remaining_quantity
        lot.status = status
        self.db.flush()
        return lot

    def apply_corporate_action_to_lot(
        self,
        lot: HoldingLot,
        new_quantity_bought: float,
        new_quantity_remaining: float,
        new_buy_price: float,
    ) -> HoldingLot:
        lot.quantity_bought = new_quantity_bought
        lot.quantity_remaining = new_quantity_remaining
        lot.buy_price = new_buy_price
        self.db.flush()
        return lot

    def get_by_id_and_user(
        self,
        lot_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> HoldingLot | None:
        """
        Ownership-scoped single-lot lookup for GET /holdings/{lot_id}. A
        mismatched owner and a genuinely nonexistent lot both fall through
        to the same None result — the caller can't distinguish "doesn't
        exist" from "exists but isn't yours" without a second query, which
        is exactly the point: don't leak whether a resource exists at all.
        """
        return (
            self.db.query(HoldingLot)
            .filter(
                HoldingLot.id == lot_id,
                HoldingLot.user_id == user_id,
            )
            .first()
        )

    def get_by_user(
        self,
        user_id: uuid.UUID
    ) -> list[HoldingLot]:
        return (
            self.db.query(HoldingLot)
            .filter(HoldingLot.user_id == user_id)
            .order_by(HoldingLot.buy_date.desc())
            .all()
        )

    def get_active_lots_by_user(
        self,
        user_id: uuid.UUID
    ) -> list[HoldingLot]:
        return (
            self.db.query(HoldingLot)
            .options(joinedload(HoldingLot.instrument))
            .filter(
                HoldingLot.user_id == user_id,
                HoldingLot.status.in_(["open", "partial"]),
            )
            .order_by(HoldingLot.buy_date.asc())
            .all()
        )

    def delete_by_user(self, user_id: uuid.UUID) -> int:
        """
        Delete all holding lots for a user. Uses flush() — the single commit
        happens in get_db(). Realized gains must be deleted first (FK RESTRICT).
        """
        deleted = (
            self.db.query(HoldingLot)
            .filter(HoldingLot.user_id == user_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted

    def delete_by_user_and_instrument_type(
        self,
        user_id: uuid.UUID,
        instrument_type: str,
    ) -> int:
        """
        Delete holding lots for a user scoped to one instrument_type (via a
        subquery on instruments.type). Used by the equity reconstruction engine
        so it only wipes equity lots and leaves crypto lots intact. Uses
        flush(). Matching realized_gains must be deleted first (FK RESTRICT).
        """
        from app.models.instrument import Instrument

        instrument_ids = (
            self.db.query(Instrument.id)
            .filter(Instrument.instrument_type == instrument_type)
            .subquery()
        )
        deleted = (
            self.db.query(HoldingLot)
            .filter(
                HoldingLot.user_id == user_id,
                HoldingLot.instrument_id.in_(instrument_ids),
            )
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted

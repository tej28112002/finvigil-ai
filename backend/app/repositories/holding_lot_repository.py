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

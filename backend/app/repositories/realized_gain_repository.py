import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.realized_gain import RealizedGain
from app.repositories.base import BaseRepository


class RealizedGainRepository(BaseRepository[RealizedGain]):
    def __init__(self, db: Session):
        super().__init__(db, RealizedGain)

    def create_realized_gain(
        self,
        user_id: uuid.UUID,
        sell_trade_id: uuid.UUID,
        holding_lot_id: uuid.UUID,
        instrument_id: uuid.UUID,
        quantity_sold: float,
        buy_price: float,
        sell_price: float,
        buy_date: datetime,
        sell_date: datetime,
        holding_days: int,
        gain_type: str,
        profit_loss: float,
    ) -> RealizedGain:
        return self.create(
            user_id=user_id,
            sell_trade_id=sell_trade_id,
            holding_lot_id=holding_lot_id,
            instrument_id=instrument_id,
            quantity_sold=quantity_sold,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_date=buy_date,
            sell_date=sell_date,
            holding_days=holding_days,
            gain_type=gain_type,
            profit_loss=profit_loss,
        )

    def get_by_user(
        self,
        user_id: uuid.UUID
    ) -> list[RealizedGain]:
        return (
            self.db.query(RealizedGain)
            .filter(RealizedGain.user_id == user_id)
            .order_by(RealizedGain.sell_date.desc())
            .all()
        )

    def get_by_instrument(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID
    ) -> list[RealizedGain]:
        return (
            self.db.query(RealizedGain)
            .filter(
                RealizedGain.user_id == user_id,
                RealizedGain.instrument_id == instrument_id,
            )
            .order_by(RealizedGain.sell_date.desc())
            .all()
        )

    def get_by_sell_trade(
        self,
        sell_trade_id: uuid.UUID
    ) -> list[RealizedGain]:
        return (
            self.db.query(RealizedGain)
            .filter(RealizedGain.sell_trade_id == sell_trade_id)
            .order_by(RealizedGain.buy_date.asc())
            .all()
        )

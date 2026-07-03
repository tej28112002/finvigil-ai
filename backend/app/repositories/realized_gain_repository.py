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
        gain_type: str | None,
        profit_loss: float,
        income_type: str = "equity_capital_gains",
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
            income_type=income_type,
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

    def get_by_user_and_income_type(
        self,
        user_id: uuid.UUID,
        income_type: str,
    ) -> list[RealizedGain]:
        return (
            self.db.query(RealizedGain)
            .filter(
                RealizedGain.user_id == user_id,
                RealizedGain.income_type == income_type,
            )
            .order_by(RealizedGain.sell_date.desc())
            .all()
        )

    def delete_by_user(self, user_id: uuid.UUID) -> int:
        """
        Delete ALL realized gains for a user (every income_type). Uses flush()
        — the single commit happens in get_db().
        """
        deleted = (
            self.db.query(RealizedGain)
            .filter(RealizedGain.user_id == user_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted

    def delete_by_user_and_income_type(
        self,
        user_id: uuid.UUID,
        income_type: str,
    ) -> int:
        """
        Delete realized gains for a user scoped to one income_type. Used by the
        equity reconstruction engine so it only wipes equity_capital_gains rows
        and leaves crypto_vda rows intact. Must run BEFORE deleting the matching
        holding_lots (FK RESTRICT). Uses flush().
        """
        deleted = (
            self.db.query(RealizedGain)
            .filter(
                RealizedGain.user_id == user_id,
                RealizedGain.income_type == income_type,
            )
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted

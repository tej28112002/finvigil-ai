import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    def __init__(self, db: Session):
        super().__init__(db, Trade)

    def get_by_user(self, user_id: uuid.UUID) -> list[Trade]:
        return self.db.query(Trade).filter(Trade.user_id == user_id).all()

    def get_by_instrument(self, instrument_id: uuid.UUID) -> list[Trade]:
        return self.db.query(Trade).filter(Trade.instrument_id == instrument_id).all()

    def create_trade(
        self,
        user_id: uuid.UUID,
        broker_connection_id: uuid.UUID,
        instrument_id: uuid.UUID,
        broker_trade_id: str,
        trade_type: str,
        quantity: float,
        price: float,
        execution_time: datetime,
        idempotency_hash: str,
    ) -> Trade:
        return self.create(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            broker_trade_id=broker_trade_id,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            execution_time=execution_time,
            idempotency_hash=idempotency_hash,
        )

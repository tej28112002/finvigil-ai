import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.instrument import Instrument
from app.models.trade import Trade
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    def __init__(self, db: Session):
        super().__init__(db, Trade)

    def get_by_user(self, user_id: uuid.UUID) -> list[Trade]:
        # joinedload(Trade.instrument): every caller that touches
        # trade.instrument in a loop (fno_pnl_service._group_fno_trades, most
        # notably) was triggering one lazy-load SQL round trip PER DISTINCT
        # INSTRUMENT — against this DB (Supabase session pooler, ap-south-1)
        # each round trip measured ~90-450ms even on an already-warm
        # connection, so 21 distinct instruments cost ~9s of pure network
        # latency on every single F&O request. One JOIN eliminates all of it.
        return (
            self.db.query(Trade)
            .options(joinedload(Trade.instrument))
            .filter(Trade.user_id == user_id)
            .all()
        )

    def get_by_user_and_instrument_type(
        self, user_id: uuid.UUID, instrument_type: str
    ) -> list[Trade]:
        """
        Same as get_by_user() but scoped to one instrument_type (e.g. "fno")
        at the SQL level via a JOIN, instead of fetching every trade the user
        has (equity + F&O + crypto) and filtering in Python after the fact —
        fewer rows transferred, and still eager-loads .instrument so no
        further lazy-load round trips happen downstream.
        """
        return (
            self.db.query(Trade)
            .join(Instrument, Trade.instrument_id == Instrument.id)
            .options(joinedload(Trade.instrument))
            .filter(
                Trade.user_id == user_id,
                Instrument.instrument_type == instrument_type,
            )
            .all()
        )

    def get_by_instrument(self, instrument_id: uuid.UUID) -> list[Trade]:
        return self.db.query(Trade).filter(Trade.instrument_id == instrument_id).all()

    def get_by_id_and_user(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Trade | None:
        """
        Ownership-scoped single-trade lookup for GET /trades/{trade_id}. A
        mismatched owner and a genuinely nonexistent trade both fall through
        to the same None result — see the matching method on
        HoldingLotRepository for why that's deliberate.
        """
        return (
            self.db.query(Trade)
            .filter(
                Trade.id == trade_id,
                Trade.user_id == user_id,
            )
            .first()
        )

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

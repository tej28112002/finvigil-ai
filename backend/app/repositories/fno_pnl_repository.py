import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.fno_pnl_entry import FnoPnlEntry
from app.repositories.base import BaseRepository


class FnoPnlRepository(BaseRepository[FnoPnlEntry]):
    def __init__(self, db: Session):
        super().__init__(db, FnoPnlEntry)

    def create_entry(
        self,
        user_id: uuid.UUID,
        instrument_id: uuid.UUID,
        buy_trade_id: uuid.UUID | None,
        sell_trade_id: uuid.UUID,
        symbol: str,
        quantity: Decimal,
        buy_price: Decimal,
        sell_price: Decimal,
        buy_time: datetime | None,
        sell_time: datetime,
        profit_loss: Decimal,
        is_intraday: bool,
        assessment_year: str,
    ) -> FnoPnlEntry:
        return self.create(
            user_id=user_id,
            instrument_id=instrument_id,
            buy_trade_id=buy_trade_id,
            sell_trade_id=sell_trade_id,
            symbol=symbol,
            quantity=quantity,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_time=buy_time,
            sell_time=sell_time,
            profit_loss=profit_loss,
            is_intraday=is_intraday,
            assessment_year=assessment_year,
        )

    def delete_by_user(self, user_id: uuid.UUID) -> int:
        """
        Delete all F&O P&L entries for a user. Used by the delete-and-rebuild
        reconstruction path. Uses flush() — the single commit happens in
        get_db().
        """
        deleted = (
            self.db.query(FnoPnlEntry)
            .filter(FnoPnlEntry.user_id == user_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return deleted

    def get_by_user(self, user_id: uuid.UUID) -> list[FnoPnlEntry]:
        return (
            self.db.query(FnoPnlEntry)
            .filter(FnoPnlEntry.user_id == user_id)
            .order_by(FnoPnlEntry.sell_time.desc())
            .all()
        )

    def get_by_user_and_ay(
        self,
        user_id: uuid.UUID,
        assessment_year: str,
    ) -> list[FnoPnlEntry]:
        return (
            self.db.query(FnoPnlEntry)
            .filter(
                FnoPnlEntry.user_id == user_id,
                FnoPnlEntry.assessment_year == assessment_year,
            )
            .order_by(FnoPnlEntry.sell_time.desc())
            .all()
        )

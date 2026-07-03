import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.tds_ledger_entry import TdsLedgerEntry
from app.repositories.base import BaseRepository


class TdsLedgerRepository(BaseRepository[TdsLedgerEntry]):
    def __init__(self, db: Session):
        super().__init__(db, TdsLedgerEntry)

    def create_entry(
        self,
        user_id: uuid.UUID,
        source_trade_id: uuid.UUID | None,
        amount: Decimal,
        timestamp: datetime,
    ) -> TdsLedgerEntry:
        return self.create(
            user_id=user_id,
            source_trade_id=source_trade_id,
            amount=amount,
            timestamp=timestamp,
        )

    def get_by_user(self, user_id: uuid.UUID) -> list[TdsLedgerEntry]:
        return (
            self.db.query(TdsLedgerEntry)
            .filter(TdsLedgerEntry.user_id == user_id)
            .order_by(TdsLedgerEntry.timestamp.desc())
            .all()
        )

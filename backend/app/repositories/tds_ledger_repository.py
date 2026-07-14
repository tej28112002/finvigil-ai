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

    def get_by_user_and_date_range(
        self,
        user_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[TdsLedgerEntry]:
        """
        Same as get_by_user() but scoped to a [start, end) timestamp range
        at the SQL level — pass get_ay_date_range(assessment_year). See the
        matching method on RealizedGainRepository for why this exists.
        """
        return (
            self.db.query(TdsLedgerEntry)
            .filter(
                TdsLedgerEntry.user_id == user_id,
                TdsLedgerEntry.timestamp >= start,
                TdsLedgerEntry.timestamp < end,
            )
            .order_by(TdsLedgerEntry.timestamp.desc())
            .all()
        )

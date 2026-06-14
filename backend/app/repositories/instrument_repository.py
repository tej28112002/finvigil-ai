from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.repositories.base import BaseRepository


class InstrumentRepository(BaseRepository[Instrument]):
    def __init__(self, db: Session):
        super().__init__(db, Instrument)

    def get_by_symbol(self, symbol: str) -> Instrument | None:
        return self.db.query(Instrument).filter(Instrument.symbol == symbol).first()

    def get_by_isin(
        self,
        isin: str
    ) -> Instrument | None:
        return self.db.query(Instrument).filter(Instrument.isin == isin).first()

    def get_or_create(
        self,
        symbol: str,
        instrument_type: str,
        name: str,
        isin: str | None = None
    ) -> Instrument:
        if isin is not None:
            existing = self.get_by_isin(isin)
            if existing:
                return existing

        existing = self.get_by_symbol(symbol)
        if existing:
            return existing

        return self.create(
            symbol=symbol,
            instrument_type=instrument_type,
            name=name,
            isin=isin
        )

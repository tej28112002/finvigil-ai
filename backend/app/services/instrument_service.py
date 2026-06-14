from app.models.instrument import Instrument
from app.repositories.instrument_repository import InstrumentRepository


class InstrumentService:
    def __init__(self, instrument_repository: InstrumentRepository):
        self.instrument_repository = instrument_repository

    def get_or_create_instrument(
        self,
        symbol: str,
        instrument_type: str,
        name: str,
        isin: str | None = None
    ) -> Instrument:
        allowed = ["equity", "fno", "mf", "crypto"]
        if instrument_type not in allowed:
            raise ValueError(
                f"Invalid instrument type: {instrument_type}. "
                f"Must be one of {allowed}"
            )

        return self.instrument_repository.get_or_create(
            symbol=symbol,
            instrument_type=instrument_type,
            name=name,
            isin=isin
        )

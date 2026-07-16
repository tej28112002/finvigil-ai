"""
Lightweight in-memory fakes for pure unit tests — no DB, no network, fast.
Each fake duck-types just the repository methods the service under test
actually calls, matching the real repositories' method signatures exactly
(cross-checked against app/repositories/*.py) so a fake passing a test says
something real about the service's logic, not about the fake's own shape.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4


@dataclass
class FakeInstrument:
    symbol: str


@dataclass
class FakeLot:
    """Stands in for app.models.holding_lot.HoldingLot."""
    quantity_remaining: Decimal
    buy_price: Decimal
    buy_date: datetime
    id: UUID = field(default_factory=uuid4)
    instrument_id: UUID = field(default_factory=uuid4)
    status: str = "open"
    instrument: FakeInstrument | None = None


class FakeHoldingLotRepository:
    """
    Matches HoldingLotRepository's method signatures used by
    HoldingLotService.consume_lots_fifo and HarvestingService.
    get_open_lots must be pre-sorted by buy_date ascending by the caller —
    same contract the real repository's ORDER BY buy_date ASC provides.
    """

    def __init__(self, lots: list[FakeLot]):
        self.lots = lots
        self.update_calls: list[tuple] = []

    def get_open_lots(self, user_id, instrument_id) -> list[FakeLot]:
        return self.lots

    def get_active_lots_by_user(self, user_id) -> list[FakeLot]:
        return self.lots

    def update_remaining_quantity(self, lot: FakeLot, remaining_quantity, status):
        lot.quantity_remaining = remaining_quantity
        lot.status = status
        self.update_calls.append((lot.id, remaining_quantity, status))
        return lot


@dataclass
class FakeGain:
    """Stands in for app.models.realized_gain.RealizedGain."""
    gain_type: str | None
    profit_loss: Decimal


class FakeRealizedGainRepository:
    def __init__(self, gains: list[FakeGain]):
        self.gains = gains

    def get_by_user_income_type_and_date_range(
        self, user_id, income_type, start, end
    ) -> list[FakeGain]:
        return self.gains


class FakeTaxSummaryRepository:
    """Captures what would have been upserted, without touching the DB."""

    def __init__(self):
        self.upserted: dict | None = None

    def get_by_user_and_year(self, user_id, assessment_year):
        return None

    def upsert_tax_summary(self, **kwargs):
        self.upserted = kwargs
        return SimpleNamespace(**kwargs)


class FakePriceService:
    def __init__(self, prices: dict[str, dict]):
        self.prices = prices

    def get_prices(self, user_id, symbols) -> dict[str, dict]:
        return self.prices

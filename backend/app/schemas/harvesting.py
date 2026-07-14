from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

_HARVEST_DISCLAIMER = (
    "Selling these positions before March 31 may reduce your tax liability "
    "by realizing the loss shown. This is not financial advice — the "
    "decision to sell, and its full tax impact, should be confirmed with "
    "your CA. Estimated tax saving assumes this loss is used to offset a "
    "capital gain in the same assessment year."
)


class HarvestCandidateResponse(BaseModel):
    lot_id: UUID
    instrument_id: UUID
    symbol: str
    quantity: Decimal
    buy_price: Decimal
    buy_date: datetime
    current_value: Decimal
    is_price_estimate: bool
    unrealized_loss: Decimal
    holding_period_days: int
    gain_type: str
    estimated_tax_saving: Decimal


class HarvestSummaryResponse(BaseModel):
    assessment_year: str
    total_harvestable_loss: Decimal
    total_estimated_tax_saving: Decimal
    candidate_count: int
    days_until_march_31: int
    disclaimer: str = _HARVEST_DISCLAIMER

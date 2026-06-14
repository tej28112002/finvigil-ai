from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PortfolioItemResponse(BaseModel):
    instrument_id: UUID
    symbol: str
    name: str
    instrument_type: str
    isin: str | None
    total_quantity: Decimal
    total_invested: Decimal
    average_buy_price: Decimal
    lot_count: int
    earliest_buy_date: datetime

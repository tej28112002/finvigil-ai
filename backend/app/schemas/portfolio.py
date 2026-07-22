from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class XirrResponse(BaseModel):
    xirr: float | None
    xirr_percent: float | None
    alpha: float | None
    alpha_percent: float | None
    beta: float | None
    benchmark: str

    absolute_return_percent: float | None
    cagr_percent: float | None
    asset_allocation: dict[str, float] | None
    top_holdings: list[dict] | None

    volatility_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    var_95_rupees: float | None


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

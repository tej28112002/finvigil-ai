from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RealizedGainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    sell_trade_id: UUID
    holding_lot_id: UUID
    instrument_id: UUID
    quantity_sold: Decimal
    buy_price: Decimal
    sell_price: Decimal
    buy_date: datetime
    sell_date: datetime
    holding_days: int
    gain_type: str | None
    income_type: str
    profit_loss: Decimal
    created_at: datetime
    updated_at: datetime

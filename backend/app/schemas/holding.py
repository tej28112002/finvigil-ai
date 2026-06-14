from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HoldingLotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    source_trade_id: UUID
    quantity_bought: Decimal
    quantity_remaining: Decimal
    buy_price: Decimal
    buy_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime

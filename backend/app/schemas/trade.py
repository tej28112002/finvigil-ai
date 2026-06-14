from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TradeIngestRequest(BaseModel):
    broker_connection_id: UUID
    broker_trade_id: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    symbol: str
    instrument_type: str
    instrument_name: str
    isin: str | None = None


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    broker_trade_id: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    idempotency_hash: str
    created_at: datetime
    updated_at: datetime

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardProjectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    total_equity_value: Decimal
    total_crypto_value: Decimal
    day_pnl: Decimal
    unrealized_pnl: Decimal
    created_at: datetime
    updated_at: datetime

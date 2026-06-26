from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CorporateActionRequest(BaseModel):
    instrument_id: UUID
    action_type: str
    ratio: Decimal
    applied_at: datetime


class CorporateActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    instrument_id: UUID
    action_type: str
    ratio: Decimal
    applied_at: datetime
    created_at: datetime
    updated_at: datetime


class CorporateActionAppliedResponse(BaseModel):
    id: UUID
    user_id: UUID
    instrument_id: UUID
    action_type: str
    ratio: Decimal
    applied_at: datetime
    lots_adjusted: int
    created_at: datetime

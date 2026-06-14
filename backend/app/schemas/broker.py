from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BrokerConnectRequest(BaseModel):
    broker_name: str
    credentials_kms_id: str | None = None


class BrokerConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    broker_name: str
    status: str
    credentials_kms_id: str | None
    created_at: datetime
    updated_at: datetime

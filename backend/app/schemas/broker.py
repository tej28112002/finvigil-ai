from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BrokerConnectRequest(BaseModel):
    broker_name: str


class BrokerCredentialsRequest(BaseModel):
    """BYOK credential intake -- POST /brokers/{broker_name}/credentials.
    api_secret required for Zerodha/Upstox; totp_secret required for Groww.
    """
    api_key: str
    api_secret: str | None = None
    totp_secret: str | None = None


class BrokerConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    broker_name: str
    status: str
    api_key: str | None
    has_credentials: bool = False
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_connection(cls, connection) -> "BrokerConnectionResponse":
        """Builds the response with has_credentials derived from the
        connection's Vault-backed fields, without ever exposing the Vault
        secret UUIDs themselves to the frontend."""
        return cls(
            id=connection.id,
            user_id=connection.user_id,
            broker_name=connection.broker_name,
            status=connection.status,
            api_key=connection.api_key,
            has_credentials=bool(
                connection.api_secret_kms_id or connection.totp_secret_kms_id
            ),
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

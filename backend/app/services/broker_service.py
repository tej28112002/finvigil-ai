from uuid import UUID

from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import BrokerConnectionRepository


class BrokerService:
    def __init__(self, broker_repository: BrokerConnectionRepository):
        self.broker_repository = broker_repository

    def get_connections(self, user_id: UUID) -> list[BrokerConnection]:
        return self.broker_repository.get_by_user(user_id)

    def connect_broker(
        self,
        user_id: UUID,
        broker_name: str,
        credentials_kms_id: str | None = None
    ) -> BrokerConnection:
        allowed = [
            "zerodha", "groww", "upstox",
            "wazirx", "coindcx", "csv"
        ]
        if broker_name not in allowed:
            raise ValueError(
                f"Invalid broker: {broker_name}. "
                f"Must be one of {allowed}"
            )

        existing = self.broker_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name=broker_name
        )
        if existing:
            raise ValueError(
                f"Broker {broker_name} is already connected."
            )

        return self.broker_repository.create_connection(
            user_id=user_id,
            broker_name=broker_name,
            credentials_kms_id=credentials_kms_id
        )

    def disconnect_broker(
        self,
        user_id: UUID,
        connection_id: UUID
    ) -> BrokerConnection:
        connection = self.broker_repository.get_by_id(connection_id)
        if not connection:
            raise ValueError(
                f"Broker connection {connection_id} not found."
            )

        if connection.user_id != user_id:
            raise ValueError(
                "You do not have permission to disconnect this broker."
            )

        return self.broker_repository.update_status(
            connection=connection,
            status="disconnected"
        )

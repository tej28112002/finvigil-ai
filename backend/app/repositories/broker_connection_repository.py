import uuid

from sqlalchemy.orm import Session

from app.models.broker_connection import BrokerConnection
from app.repositories.base import BaseRepository


class BrokerConnectionRepository(BaseRepository[BrokerConnection]):
    def __init__(self, db: Session):
        super().__init__(db, BrokerConnection)

    def get_by_user(self, user_id: uuid.UUID) -> list[BrokerConnection]:
        return (
            self.db.query(BrokerConnection)
            .filter(BrokerConnection.user_id == user_id)
            .order_by(BrokerConnection.created_at.desc())
            .all()
        )

    def get_by_user_and_broker(
        self, user_id: uuid.UUID, broker_name: str
    ) -> BrokerConnection | None:
        return (
            self.db.query(BrokerConnection)
            .filter(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker_name == broker_name,
            )
            .first()
        )

    def create_connection(
        self,
        user_id: uuid.UUID,
        broker_name: str,
        api_key: str | None = None,
        api_secret_kms_id: str | None = None,
    ) -> BrokerConnection:
        return self.create(
            user_id=user_id,
            broker_name=broker_name,
            status="active",
            api_key=api_key,
            api_secret_kms_id=api_secret_kms_id,
        )

    def update_status(
        self, connection: BrokerConnection, status: str
    ) -> BrokerConnection:
        connection.status = status
        self.db.flush()
        return connection

    def update_api_key(
        self,
        connection: BrokerConnection,
        api_key: str,
    ) -> BrokerConnection:
        connection.api_key = api_key
        self.db.flush()
        return connection

    def update_api_secret_kms_id(
        self,
        connection: BrokerConnection,
        api_secret_kms_id: str,
    ) -> BrokerConnection:
        connection.api_secret_kms_id = api_secret_kms_id
        self.db.flush()
        return connection

    def update_access_token_kms_id(
        self,
        connection: BrokerConnection,
        access_token_kms_id: str,
    ) -> BrokerConnection:
        connection.access_token_kms_id = access_token_kms_id
        self.db.flush()
        return connection

    def update_totp_secret_kms_id(
        self,
        connection: BrokerConnection,
        totp_secret_kms_id: str,
    ) -> BrokerConnection:
        connection.totp_secret_kms_id = totp_secret_kms_id
        self.db.flush()
        return connection

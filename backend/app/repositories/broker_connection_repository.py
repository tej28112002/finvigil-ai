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
        credentials_kms_id: str | None,
    ) -> BrokerConnection:
        return self.create(
            user_id=user_id,
            broker_name=broker_name,
            status="active",
            credentials_kms_id=credentials_kms_id,
        )

    def update_status(
        self, connection: BrokerConnection, status: str
    ) -> BrokerConnection:
        connection.status = status
        self.db.flush()
        return connection

    def update_credentials_kms_id(
        self,
        connection: BrokerConnection,
        credentials_kms_id: str,
    ) -> BrokerConnection:
        connection.credentials_kms_id = credentials_kms_id
        self.db.flush()
        return connection

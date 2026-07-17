from uuid import UUID

from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.vault_repository import VaultRepository

# Brokers with a BYOK credential-intake flow (POST /brokers/{broker}/credentials).
# Extend as Groww lands (Phase 16 sequencing: Zerodha -> Upstox -> Groww).
BYOK_BROKERS = ["zerodha", "upstox", "groww"]


class BrokerService:
    def __init__(
        self,
        broker_repository: BrokerConnectionRepository,
        vault_repository: VaultRepository | None = None,
    ):
        self.broker_repository = broker_repository
        self.vault_repository = vault_repository

    def get_connections(self, user_id: UUID) -> list[BrokerConnection]:
        return self.broker_repository.get_by_user(user_id)

    def connect_broker(
        self,
        user_id: UUID,
        broker_name: str,
    ) -> BrokerConnection:
        """
        Create a bare broker_connections row with no credentials attached.
        Used for brokers that don't need BYOK setup (csv, wazirx, coindcx).
        Zerodha/Upstox/Groww go through submit_credentials() instead, which
        creates the row itself if one doesn't exist yet.
        """
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
        )

    def submit_credentials(
        self,
        user_id: UUID,
        broker_name: str,
        api_key: str,
        api_secret: str | None = None,
        totp_secret: str | None = None,
    ) -> BrokerConnection:
        """
        Store a user's own broker app credentials (BYOK). api_key is written
        plain (it's a client identifier, not a secret -- Kite Connect's own
        docs draw this same line). api_secret/totp_secret are Vault-wrapped,
        same pattern ZerodhaService already uses for the access token.
        """
        if broker_name not in BYOK_BROKERS:
            raise ValueError(
                f"BYOK credentials are not supported for {broker_name} yet. "
                f"Must be one of {BYOK_BROKERS}"
            )
        if self.vault_repository is None:
            raise ValueError(
                "Vault repository is required to store broker secrets."
            )
        if not api_key:
            raise ValueError("api_key is required.")

        connection = self.broker_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name=broker_name,
        )
        if not connection:
            connection = self.broker_repository.create_connection(
                user_id=user_id,
                broker_name=broker_name,
            )

        self.broker_repository.update_api_key(connection, api_key)

        if api_secret:
            self._store_secret(
                connection=connection,
                secret_value=api_secret,
                existing_kms_id=connection.api_secret_kms_id,
                vault_name=f"{broker_name}_api_secret_{user_id}",
                description=f"{broker_name.capitalize()} API secret",
                update=self.broker_repository.update_api_secret_kms_id,
            )

        if totp_secret:
            self._store_secret(
                connection=connection,
                secret_value=totp_secret,
                existing_kms_id=connection.totp_secret_kms_id,
                vault_name=f"{broker_name}_totp_secret_{user_id}",
                description=f"{broker_name.capitalize()} TOTP secret",
                update=self.broker_repository.update_totp_secret_kms_id,
            )

        return connection

    def _store_secret(
        self,
        connection: BrokerConnection,
        secret_value: str,
        existing_kms_id: str | None,
        vault_name: str,
        description: str,
        update,
    ) -> None:
        if existing_kms_id:
            self.vault_repository.update_secret(
                secret_id=UUID(existing_kms_id),
                secret_value=secret_value,
                name=vault_name,
                description=description,
            )
        else:
            secret_id = self.vault_repository.create_secret(
                secret_value=secret_value,
                name=vault_name,
                description=description,
            )
            update(connection, str(secret_id))

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

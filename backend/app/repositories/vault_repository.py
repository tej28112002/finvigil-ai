import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


class VaultRepository:
    """
    Handles Supabase Vault interactions for storing per-user
    secrets (Zerodha access tokens).

    Vault functions are Postgres functions, not ORM tables, so
    this repository uses parameterized raw SQL. All values are
    bound as parameters (never string-formatted) to prevent
    SQL injection, since the secret value is sensitive.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_secret(
        self,
        secret_value: str,
        name: str,
        description: str = "",
    ) -> uuid.UUID:
        """
        Store a new secret in Vault.
        Returns the Vault secret UUID, which the caller stores
        in broker_connections.credentials_kms_id.
        """
        result = self.db.execute(
            text(
                "SELECT vault.create_secret("
                ":secret_value, :name, :description"
                ") AS secret_id"
            ),
            {
                "secret_value": secret_value,
                "name": name,
                "description": description,
            },
        )
        row = result.first()
        return row.secret_id

    def update_secret(
        self,
        secret_id: uuid.UUID,
        secret_value: str,
        name: str,
        description: str = "",
    ) -> None:
        """
        Update an existing Vault secret in place (same UUID,
        new value). Used for the daily access-token refresh.
        """
        self.db.execute(
            text(
                "SELECT vault.update_secret("
                ":secret_id, :secret_value, :name, :description"
                ")"
            ),
            {
                "secret_id": str(secret_id),
                "secret_value": secret_value,
                "name": name,
                "description": description,
            },
        )

    def get_secret(
        self,
        secret_id: uuid.UUID,
    ) -> str | None:
        """
        Retrieve and decrypt a secret by its Vault UUID.
        Returns the plaintext secret, or None if not found.
        """
        result = self.db.execute(
            text(
                "SELECT decrypted_secret "
                "FROM vault.decrypted_secrets "
                "WHERE id = :secret_id"
            ),
            {"secret_id": str(secret_id)},
        )
        row = result.first()
        if row is None:
            return None
        return row.decrypted_secret

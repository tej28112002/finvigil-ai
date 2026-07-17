import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.trade import Trade


class BrokerConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "broker_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_name", name="uq_broker_connections_user_broker"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    broker_name: Mapped[str] = mapped_column(
        Enum(
            "zerodha", "groww", "upstox", "wazirx", "coindcx", "csv",
            name="broker_name_enum",
            create_type=False,
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "active", "disconnected", "syncing", "error",
            name="broker_status_enum",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'active'"),
    )
    # BYOK (Phase 16): each user supplies their own broker app credentials.
    # api_key is a client identifier, not a secret (Kite Connect's own docs
    # say as much) -- stored plain. The other three are genuine secrets and
    # live in Supabase Vault, referenced here by their vault.secrets UUID.
    api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    api_secret_kms_id: Mapped[str | None] = mapped_column(String, nullable=True)
    access_token_kms_id: Mapped[str | None] = mapped_column(String, nullable=True)
    totp_secret_kms_id: Mapped[str | None] = mapped_column(String, nullable=True)

    trades: Mapped[List["Trade"]] = relationship(
        back_populates="broker_connection",
        cascade="all, delete-orphan",
    )

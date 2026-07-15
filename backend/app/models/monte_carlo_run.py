import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MonteCarloRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monte_carlo_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    replay_scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replay_scenarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    result_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

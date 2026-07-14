import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReplayRun(UUIDMixin, TimestampMixin, Base):
    """
    One executed snapshot of a ReplayScenario: the reconstructed equity
    portfolio state (open holdings + realized P&L) as of the scenario's
    as_of_date, computed by replaying trades in-memory via FIFO (see
    ReplayService._replay_fifo). Never written to holding_lots /
    realized_gains — those stay the live, present-day derived tables; a
    replay is a parallel, read-only computation persisted only here as a
    JSONB snapshot (see app.schemas.replay.ReplayResultData for the shape).
    """

    __tablename__ = "replay_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    replay_scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replay_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

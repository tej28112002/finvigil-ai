import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReplayScenario(UUIDMixin, TimestampMixin, Base):
    """
    A saved Portfolio Replay definition: an "as of" date to rewind the
    portfolio to, plus optional hypothetical (what-if) trades layered on top
    of the user's real trade history. Stores only the INPUT parameters as
    JSONB (see app.schemas.replay.ReplayParameters for the shape) — running
    the scenario produces a separate ReplayRun snapshot, so the same
    scenario can be re-run multiple times as real trade data changes.
    """

    __tablename__ = "replay_scenarios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

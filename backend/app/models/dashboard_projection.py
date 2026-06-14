import uuid

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DashboardProjection(TimestampMixin, Base):
    __tablename__ = "dashboard_projections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    total_equity_value: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    total_crypto_value: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    day_pnl: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Numeric(18, 8),
        nullable=False,
    )

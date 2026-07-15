import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Subscription(UUIDMixin, TimestampMixin, Base):
    """
    One user's billing plan/status (BRD §10). is_active is a legacy nullable
    flag on the live table, separate from `status` — kept distinct rather
    than collapsed into `status` since the DB already defines both and
    changing that is out of this phase's scope. Entitlement (Pro/Premium
    access, including the 7-day payment-grace window) is DERIVED from
    plan_id + status + current_period_end by SubscriptionService, not
    stored directly on this row.
    """

    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str] = mapped_column(
        ENUM(
            "free", "pro_monthly", "pro_annual",
            "premium_monthly", "premium_annual",
            name="subscription_plan_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="free",
    )
    status: Mapped[str] = mapped_column(
        ENUM(
            "active", "past_due", "canceled", "grace",
            name="subscription_status_enum",
            create_type=False,
        ),
        nullable=False,
        server_default="active",
    )
    is_active: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        server_default="true",
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

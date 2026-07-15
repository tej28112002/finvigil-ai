import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db: Session):
        super().__init__(db, Subscription)

    def get_by_user(self, user_id: uuid.UUID) -> Subscription | None:
        return (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .first()
        )

    def create_default_free(self, user_id: uuid.UUID) -> Subscription:
        return self.create(
            user_id=user_id,
            plan_id="free",
            status="active",
            is_active=True,
        )

    def update_status(
        self,
        subscription: Subscription,
        plan_id: str | None = None,
        status: str | None = None,
        current_period_end: datetime | None = None,
        is_active: bool | None = None,
    ) -> Subscription:
        """Partial update — only fields explicitly passed are changed."""
        if plan_id is not None:
            subscription.plan_id = plan_id
        if status is not None:
            subscription.status = status
        if current_period_end is not None:
            subscription.current_period_end = current_period_end
        if is_active is not None:
            subscription.is_active = is_active
        self.db.flush()
        self.db.refresh(subscription)
        return subscription

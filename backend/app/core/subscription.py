from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService


def check_subscription_tier(db: Session, user_id: UUID) -> bool:
    """
    Returns True if the user currently has Pro/Premium-level access — an
    active Pro/Premium subscription, or one within its 7-day payment-grace
    window (BRD §10). Returns False for Free, canceled, or a subscription
    whose grace window has already expired. Reads app.models.subscription
    via SubscriptionService — no longer a stub that lets everyone through.
    """
    service = SubscriptionService(SubscriptionRepository(db))
    return service.check_subscription_tier(user_id)

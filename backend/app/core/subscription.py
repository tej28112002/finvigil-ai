from uuid import UUID

from sqlalchemy.orm import Session


def check_subscription_tier(db: Session, user_id: UUID) -> bool:
    """
    Returns True if the user is on a Pro or Premium plan.
    Returns False (→ caller raises 403) if on the Free tier.

    Currently allows all users through (subscription/billing model is
    unbuilt — BRD §10 Razorpay integration is a future phase). When the
    Subscription table and Razorpay webhooks land, this will query
    subscriptions.plan_id for the user and gate on plan_pro_* /
    plan_premium_*.
    """
    return True

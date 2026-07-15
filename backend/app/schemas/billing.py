from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    plan_id: str
    status: str
    is_active: bool
    current_period_end: datetime | None
    is_pro_or_premium: bool
    in_grace_period: bool
    grace_deadline: datetime | None


class CreateSubscriptionRequest(BaseModel):
    plan_id: str  # one of: pro_monthly, pro_annual, premium_monthly, premium_annual


class CreateSubscriptionResponse(BaseModel):
    razorpay_subscription_id: str
    checkout_url: str | None

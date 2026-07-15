import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core import razorpay_client
from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.billing import (
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    SubscriptionResponse,
)
from app.services.subscription_service import PRO_PREMIUM_PLANS, SubscriptionService

router = APIRouter()


def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(SubscriptionRepository(db))


@router.get("/billing/subscription", response_model=SubscriptionResponse)
def get_subscription(
    user_id: UUID = Depends(get_current_user_id),
    service: SubscriptionService = Depends(get_subscription_service),
):
    # reconcile_expired_grace also creates a default Free row for a user
    # who has never touched billing — GET always returns something, never 404.
    subscription = service.reconcile_expired_grace(user_id)
    entitlement = service.compute_effective_entitlement(subscription)
    return SubscriptionResponse(
        plan_id=subscription.plan_id,
        status=subscription.status,
        is_active=subscription.is_active if subscription.is_active is not None else True,
        current_period_end=subscription.current_period_end,
        is_pro_or_premium=entitlement["is_pro_or_premium"],
        in_grace_period=entitlement["in_grace_period"],
        grace_deadline=entitlement["grace_deadline"],
    )


@router.post("/billing/create-subscription", response_model=CreateSubscriptionResponse)
def create_subscription(
    request: CreateSubscriptionRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    if request.plan_id not in PRO_PREMIUM_PLANS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan_id. Must be one of: {sorted(PRO_PREMIUM_PLANS)}",
        )

    razorpay_plan_id = razorpay_client.get_razorpay_plan_id(request.plan_id)
    if not razorpay_plan_id:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Razorpay plan mapping for '{request.plan_id}' is not "
                f"configured yet. An admin must create this plan in the "
                f"Razorpay dashboard and set the matching RAZORPAY_PLAN_* "
                f"variable in backend/.env."
            ),
        )

    try:
        razorpay_subscription = razorpay_client.create_subscription(
            razorpay_plan_id=razorpay_plan_id,
            notes={
                "finvigil_user_id": str(user_id),
                "finvigil_plan_id": request.plan_id,
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay request failed: {e}")

    return CreateSubscriptionResponse(
        razorpay_subscription_id=razorpay_subscription["id"],
        checkout_url=razorpay_subscription.get("short_url"),
    )


@router.post("/billing/cancel-subscription", response_model=SubscriptionResponse)
def cancel_subscription(
    user_id: UUID = Depends(get_current_user_id),
    service: SubscriptionService = Depends(get_subscription_service),
):
    # LIMITATION: only updates FinVigil's own record — see
    # SubscriptionService.cancel_subscription's docstring. Does not call
    # Razorpay's cancel API (no razorpay_subscription_id is persisted).
    subscription = service.cancel_subscription(user_id)
    entitlement = service.compute_effective_entitlement(subscription)
    return SubscriptionResponse(
        plan_id=subscription.plan_id,
        status=subscription.status,
        is_active=subscription.is_active if subscription.is_active is not None else True,
        current_period_end=subscription.current_period_end,
        is_pro_or_premium=entitlement["is_pro_or_premium"],
        in_grace_period=entitlement["in_grace_period"],
        grace_deadline=entitlement["grace_deadline"],
    )


@router.post("/billing/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    # NO get_current_user_id here — Razorpay calling this endpoint has no
    # FinVigil user session; it authenticates via the HMAC signature below
    # instead. Same deliberate, documented exception as
    # /brokers/zerodha/callback (see docs/project-context.md).
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not razorpay_client.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed webhook payload.")

    event_type = payload.get("event", "")
    subscription_entity = (
        payload.get("payload", {}).get("subscription", {}).get("entity", {})
    )

    service = SubscriptionService(SubscriptionRepository(db))
    try:
        service.handle_webhook_event(event_type, subscription_entity)
    except ValueError as e:
        # Signature WAS valid — this is a data problem (e.g. no
        # notes.finvigil_user_id), not an auth failure.
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok"}

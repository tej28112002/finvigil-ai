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
from app.services.subscription_service import SubscriptionService

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
    service: SubscriptionService = Depends(get_subscription_service),
):
    try:
        result = service.create_subscription(
            user_id=user_id, finvigil_plan_id=request.plan_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay request failed: {e}")

    return CreateSubscriptionResponse(**result)


@router.post("/billing/cancel-subscription", response_model=SubscriptionResponse)
def cancel_subscription(
    user_id: UUID = Depends(get_current_user_id),
    service: SubscriptionService = Depends(get_subscription_service),
):
    # Calls Razorpay's cancel API when a razorpay_subscription_id is on
    # record; local status always moves to 'canceled' regardless of that
    # call's outcome — see SubscriptionService.cancel_subscription.
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

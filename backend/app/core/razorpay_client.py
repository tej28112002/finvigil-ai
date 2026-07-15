import hashlib
import hmac

import requests

from app.core.config import settings

_RAZORPAY_API_BASE = "https://api.razorpay.com/v1"

# FinVigil's own plan_id enum -> the actual Razorpay plan_id created in the
# Razorpay dashboard (Subscriptions > Plans). These are NOT the same string
# — Razorpay assigns its own plan_xxxxx IDs, configured in backend/.env.
_PLAN_ID_MAP = {
    "pro_monthly": settings.RAZORPAY_PLAN_PRO_MONTHLY,
    "pro_annual": settings.RAZORPAY_PLAN_PRO_ANNUAL,
    "premium_monthly": settings.RAZORPAY_PLAN_PREMIUM_MONTHLY,
    "premium_annual": settings.RAZORPAY_PLAN_PREMIUM_ANNUAL,
}


def get_razorpay_plan_id(finvigil_plan_id: str) -> str | None:
    return _PLAN_ID_MAP.get(finvigil_plan_id) or None


def is_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """
    Verifies X-Razorpay-Signature = HMAC-SHA256(webhook_secret, raw_body).
    NEVER trust a webhook payload without this passing first — it is the
    only thing standing between this endpoint and a forged event (e.g.
    someone POSTing a fake "subscription.activated" to grant themselves
    Pro for free). Returns False (not raises) so the caller can respond
    with a clean 400 rather than a 500 on bad/missing signatures.
    Constant-time comparison (hmac.compare_digest) to avoid timing attacks.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def create_subscription(razorpay_plan_id: str, notes: dict, total_count: int = 12) -> dict:
    """
    Calls Razorpay's Create Subscription API (test mode — RAZORPAY_KEY_ID/
    SECRET must be TEST keys per this project's rule to never use
    production keys in code/dev). Raises RuntimeError (not a network call)
    if Razorpay isn't configured yet, so this fails clearly instead of
    attempting a request that can only error out.
    """
    if not is_configured():
        raise RuntimeError(
            "Razorpay is not configured. Set RAZORPAY_KEY_ID and "
            "RAZORPAY_KEY_SECRET in backend/.env (test-mode keys from the "
            "Razorpay dashboard) before creating subscriptions."
        )
    response = requests.post(
        f"{_RAZORPAY_API_BASE}/subscriptions",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={
            "plan_id": razorpay_plan_id,
            "total_count": total_count,
            "notes": notes,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def cancel_subscription(razorpay_subscription_id: str) -> dict:
    """
    Calls Razorpay's Cancel Subscription API. Razorpay's real endpoint is
    POST /v1/subscriptions/{id}/cancel (not DELETE — cancellation is an
    action on the subscription resource, not a resource deletion; a DELETE
    verb here would just 405 against the real API).
    cancel_at_cycle_end=0 means cancel immediately, not at the end of the
    current billing cycle.
    """
    if not is_configured():
        raise RuntimeError(
            "Razorpay is not configured. Set RAZORPAY_KEY_ID and "
            "RAZORPAY_KEY_SECRET in backend/.env before canceling subscriptions."
        )
    response = requests.post(
        f"{_RAZORPAY_API_BASE}/subscriptions/{razorpay_subscription_id}/cancel",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={"cancel_at_cycle_end": 0},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core import razorpay_client
from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository

GRACE_PERIOD_DAYS = 7
PRO_PREMIUM_PLANS = {"pro_monthly", "pro_annual", "premium_monthly", "premium_annual"}

# subscription_status_enum has 4 values in the live DB: active, past_due,
# canceled, grace. The webhook handler below sets 'past_due' immediately on
# a failed charge (matching the literal event mapping this phase was
# built against); 'grace' is reserved for a future reconciliation job to
# explicitly mark "confirmed within the 7-day window" rather than left
# implicitly inferred every time — not required for entitlement CORRECTNESS
# (compute_effective_entitlement treats 'past_due' and 'grace' identically),
# only for clearer reporting. Both are checked the same way here.
_GRACE_ELIGIBLE_STATUSES = {"past_due", "grace"}


class SubscriptionService:
    """
    Owns the subscription state machine (BRD §10): entitlement derivation
    (including the 7-day payment-grace window), Razorpay webhook event
    application, and lazy downgrade-on-read for expired grace periods.
    """

    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    def get_or_create_subscription(self, user_id: UUID) -> Subscription:
        subscription = self.subscription_repository.get_by_user(user_id)
        if subscription:
            return subscription
        return self.subscription_repository.create_default_free(user_id)

    def compute_effective_entitlement(self, subscription: Subscription) -> dict:
        """
        Pure read — no DB writes. Safe to call on every request (this is
        what check_subscription_tier() delegates to for every Pro-gated
        endpoint). Returns whether the subscription IS pro/premium right
        now, accounting for the grace window, without requiring the DB
        row to have already been reconciled/downgraded.
        """
        now = datetime.now(timezone.utc)

        if subscription.plan_id not in PRO_PREMIUM_PLANS:
            return {
                "is_pro_or_premium": False,
                "in_grace_period": False,
                "grace_deadline": None,
            }

        if subscription.status == "active":
            return {
                "is_pro_or_premium": True,
                "in_grace_period": False,
                "grace_deadline": None,
            }

        if subscription.status in _GRACE_ELIGIBLE_STATUSES and subscription.current_period_end:
            grace_deadline = subscription.current_period_end + timedelta(
                days=GRACE_PERIOD_DAYS
            )
            if now <= grace_deadline:
                return {
                    "is_pro_or_premium": True,
                    "in_grace_period": True,
                    "grace_deadline": grace_deadline,
                }
            return {
                "is_pro_or_premium": False,
                "in_grace_period": False,
                "grace_deadline": grace_deadline,
            }

        # status == 'canceled', or past_due/grace with no current_period_end
        # on record (can't compute a grace window at all — fail closed).
        return {
            "is_pro_or_premium": False,
            "in_grace_period": False,
            "grace_deadline": None,
        }

    def check_subscription_tier(self, user_id: UUID) -> bool:
        """
        Entry point used by app.core.subscription.check_subscription_tier()
        and every Pro-gated endpoint. No subscription row at all (a user
        who has never touched billing) is treated as Free — False.
        """
        subscription = self.subscription_repository.get_by_user(user_id)
        if not subscription:
            return False
        return self.compute_effective_entitlement(subscription)["is_pro_or_premium"]

    def reconcile_expired_grace(self, user_id: UUID) -> Subscription:
        """
        Ensures a subscription row exists, and if it's past_due/grace with
        an expired grace window, downgrades it to plan_id='free' in the DB
        (BRD §10: "After day 7: downgrade to Free"). Idempotent — safe to
        call repeatedly. Called from GET /billing/subscription as a
        lazy, read-triggered reconciliation; NOT called from
        check_subscription_tier() itself, which must stay a pure read so
        every Pro-gated request doesn't carry a surprise write.

        No Celery/scheduled job exists yet to do this proactively (Phase 12
        Celery+Redis is still open) — until then, a lapsed subscription's DB
        row only updates the next time the user (or this endpoint) looks at
        it, though check_subscription_tier() already computes the correct
        answer live regardless of whether this reconciliation has run.
        """
        subscription = self.get_or_create_subscription(user_id)
        entitlement = self.compute_effective_entitlement(subscription)

        grace_expired = (
            subscription.plan_id in PRO_PREMIUM_PLANS
            and subscription.status in _GRACE_ELIGIBLE_STATUSES
            and not entitlement["is_pro_or_premium"]
        )
        if grace_expired:
            subscription = self.subscription_repository.update_status(
                subscription, plan_id="free", status="active", is_active=True
            )
        return subscription

    def create_subscription(self, user_id: UUID, finvigil_plan_id: str) -> dict:
        """
        Orchestrates Razorpay subscription creation end-to-end: resolves
        FinVigil's plan_id to Razorpay's actual dashboard-created plan_id,
        calls Razorpay's Create Subscription API, then immediately persists
        the returned razorpay_subscription_id on this user's local row —
        without that, a later webhook or cancel_subscription() call has
        nothing to correlate/act on for this subscription.
        """
        if finvigil_plan_id not in PRO_PREMIUM_PLANS:
            raise ValueError(
                f"Invalid plan_id. Must be one of: {sorted(PRO_PREMIUM_PLANS)}"
            )

        razorpay_plan_id = razorpay_client.get_razorpay_plan_id(finvigil_plan_id)
        if not razorpay_plan_id:
            raise RuntimeError(
                f"Razorpay plan mapping for '{finvigil_plan_id}' is not "
                f"configured. An admin must create this plan in the "
                f"Razorpay dashboard and set the matching RAZORPAY_PLAN_* "
                f"variable in backend/.env."
            )

        razorpay_subscription = razorpay_client.create_subscription(
            razorpay_plan_id=razorpay_plan_id,
            notes={
                "finvigil_user_id": str(user_id),
                "finvigil_plan_id": finvigil_plan_id,
            },
        )

        subscription = self.get_or_create_subscription(user_id)
        self.subscription_repository.update_status(
            subscription,
            razorpay_subscription_id=razorpay_subscription["id"],
        )

        return {
            "razorpay_subscription_id": razorpay_subscription["id"],
            "checkout_url": razorpay_subscription.get("short_url"),
        }

    def cancel_subscription(self, user_id: UUID) -> Subscription:
        """
        User-initiated cancellation (billing page "Cancel subscription").
        If a razorpay_subscription_id is on record, also calls Razorpay's
        Cancel Subscription API — but the LOCAL DB is always updated to
        status='canceled' regardless of whether that call succeeds, so
        FinVigil's own access control never depends on Razorpay's API
        being reachable at that moment. A subscription with no
        razorpay_subscription_id on record (e.g. never went through
        create_subscription(), or predates that correlation being stored)
        only has its local record changed — nothing exists to tell
        Razorpay to stop billing, so that would need to be done manually
        in the Razorpay dashboard.
        """
        subscription = self.get_or_create_subscription(user_id)

        if subscription.razorpay_subscription_id:
            try:
                razorpay_client.cancel_subscription(subscription.razorpay_subscription_id)
            except Exception:
                # Local cancellation intent must still be honored even if
                # Razorpay is unreachable or errors — never leave a user
                # stuck paying because of a transient API failure.
                pass

        return self.subscription_repository.update_status(
            subscription, status="canceled", is_active=False
        )

    def handle_webhook_event(self, event_type: str, subscription_entity: dict) -> None:
        """
        Applies one Razorpay subscription webhook event. Called ONLY after
        the caller has verified the request's HMAC signature — this method
        trusts subscription_entity completely, so it must never be reached
        from an unverified payload.

        Correlates the event to a FinVigil user via
        subscription_entity["notes"]["finvigil_user_id"] — set by this app
        itself when the subscription was created (POST
        /billing/create-subscription). The live `subscriptions` table has
        no razorpay_subscription_id column to correlate by instead; adding
        one would need a schema change beyond this phase's authorized SQL.
        """
        notes = subscription_entity.get("notes") or {}
        user_id_str = notes.get("finvigil_user_id")
        if not user_id_str:
            raise ValueError(
                "Webhook subscription has no notes.finvigil_user_id — "
                "cannot correlate this event to a FinVigil user."
            )
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise ValueError(f"notes.finvigil_user_id is not a valid UUID: {user_id_str!r}")

        subscription = self.get_or_create_subscription(user_id)
        current_period_end = self._parse_current_end(subscription_entity)

        if event_type == "subscription.activated":
            plan_id = notes.get("finvigil_plan_id") or subscription.plan_id
            self.subscription_repository.update_status(
                subscription,
                plan_id=plan_id,
                status="active",
                current_period_end=current_period_end,
                is_active=True,
            )
        elif event_type == "subscription.charged":
            self.subscription_repository.update_status(
                subscription,
                status="active",
                current_period_end=current_period_end,
                is_active=True,
            )
        elif event_type == "subscription.cancelled":
            self.subscription_repository.update_status(
                subscription, status="canceled", is_active=False
            )
        elif event_type == "subscription.halted":
            self.subscription_repository.update_status(
                subscription, status="past_due"
            )
        elif event_type == "subscription.resumed":
            self.subscription_repository.update_status(
                subscription, status="active", is_active=True
            )
        # Razorpay sends many other event types (invoice.*, payment.*,
        # subscription.pending, ...) that this app doesn't model yet —
        # silently ignored rather than treated as an error, since an
        # unrecognized-but-validly-signed event is not a failure.

    @staticmethod
    def _parse_current_end(subscription_entity: dict):
        current_end = subscription_entity.get("current_end")
        if current_end is None:
            return None
        return datetime.fromtimestamp(current_end, tz=timezone.utc)

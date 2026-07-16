"""
Billing/subscription logic (Phase 15.1 continuation, priority #4) --
SubscriptionService: entitlement/grace-period math, webhook state
machine, and (given today's real Razorpay plan-ID mix-up) a live check
that each FinVigil tier maps to the CORRECT, distinct Razorpay plan --
not just "a plan ID exists". Grace-period boundaries below (past-due 2
days = entitled, past-due 10 days = not entitled) are the exact cases
requested; both hand-computed against BRD Section 10's stated "7 full
days from first failed charge" rule before writing the assertions.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.subscription_service import SubscriptionService
from tests.fakes import FakeSubscription, FakeSubscriptionRepository

NOW = datetime.now(timezone.utc)


def make_service(subscription=None):
    repo = FakeSubscriptionRepository(subscription)
    return SubscriptionService(subscription_repository=repo), repo


class TestCheckSubscriptionTier:
    def test_no_subscription_row_is_free(self):
        service, _ = make_service(subscription=None)
        assert service.check_subscription_tier(uuid4()) is False

    def test_free_plan_active_status_not_entitled(self):
        sub = FakeSubscription(plan_id="free", status="active")
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is False

    def test_pro_monthly_active_is_entitled(self):
        sub = FakeSubscription(plan_id="pro_monthly", status="active")
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is True

    def test_canceled_pro_plan_not_entitled(self):
        sub = FakeSubscription(plan_id="pro_monthly", status="canceled")
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is False

    def test_past_due_2_days_still_entitled(self):
        """
        Requested exact case: past-due 2 days = entitled. BRD Section 10:
        "Grace: 7 full days from first failed charge -- full Pro/Premium
        access." current_period_end 2 days ago -> grace_deadline is 5 days
        in the future -> still within the window.
        """
        sub = FakeSubscription(
            plan_id="pro_monthly", status="past_due",
            current_period_end=NOW - timedelta(days=2),
        )
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is True

        entitlement = service.compute_effective_entitlement(sub)
        assert entitlement["in_grace_period"] is True

    def test_past_due_10_days_no_longer_entitled(self):
        """
        Requested exact case: past-due 10 days = not entitled. 10 days
        exceeds the 7-day grace window (BRD Section 10) by 3 days ->
        grace_deadline was 3 days ago -> access must be gone.
        """
        sub = FakeSubscription(
            plan_id="pro_monthly", status="past_due",
            current_period_end=NOW - timedelta(days=10),
        )
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is False

        entitlement = service.compute_effective_entitlement(sub)
        assert entitlement["in_grace_period"] is False
        assert entitlement["is_pro_or_premium"] is False

    def test_past_due_with_no_current_period_end_fails_closed(self):
        """Can't compute a grace window without a reference point -- must
        deny access rather than assume entitled."""
        sub = FakeSubscription(plan_id="pro_monthly", status="past_due", current_period_end=None)
        service, _ = make_service(sub)
        assert service.check_subscription_tier(uuid4()) is False


class TestReconcileExpiredGrace:
    def test_downgrades_to_free_when_grace_expired(self):
        sub = FakeSubscription(
            plan_id="pro_monthly", status="past_due",
            current_period_end=NOW - timedelta(days=10),
        )
        service, repo = make_service(sub)

        result = service.reconcile_expired_grace(sub.user_id)

        assert result.plan_id == "free"
        assert result.status == "active"

    def test_does_not_downgrade_while_still_in_grace(self):
        sub = FakeSubscription(
            plan_id="pro_monthly", status="past_due",
            current_period_end=NOW - timedelta(days=2),
        )
        service, _ = make_service(sub)

        result = service.reconcile_expired_grace(sub.user_id)

        assert result.plan_id == "pro_monthly"  # untouched
        assert result.status == "past_due"

    def test_active_subscription_is_never_touched(self):
        sub = FakeSubscription(plan_id="pro_monthly", status="active")
        service, _ = make_service(sub)

        result = service.reconcile_expired_grace(sub.user_id)

        assert result.plan_id == "pro_monthly"
        assert result.status == "active"


class TestWebhookStateMachine:
    def _sub_with_notes(self, user_id):
        return {"notes": {"finvigil_user_id": str(user_id)}}

    def test_activated_sets_active_and_plan_id(self):
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="free", status="active")
        service, _ = make_service(sub)

        service.handle_webhook_event(
            "subscription.activated",
            {"notes": {"finvigil_user_id": str(user_id), "finvigil_plan_id": "pro_monthly"}, "current_end": None},
        )

        assert sub.plan_id == "pro_monthly"
        assert sub.status == "active"
        assert sub.is_active is True

    def test_charged_keeps_active_without_changing_plan_id(self):
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="premium_annual", status="active")
        service, _ = make_service(sub)

        service.handle_webhook_event("subscription.charged", {"notes": {"finvigil_user_id": str(user_id)}, "current_end": None})

        assert sub.status == "active"
        assert sub.plan_id == "premium_annual"  # unchanged -- charged never touches plan_id

    def test_cancelled_sets_canceled_and_inactive(self):
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="pro_monthly", status="active", is_active=True)
        service, _ = make_service(sub)

        service.handle_webhook_event("subscription.cancelled", {"notes": {"finvigil_user_id": str(user_id)}})

        assert sub.status == "canceled"
        assert sub.is_active is False

    def test_halted_sets_past_due_without_killing_access_immediately(self):
        """
        halted -> status becomes past_due, matching BRD's grace model
        (still entitled until the 7-day window actually expires, checked
        separately by compute_effective_entitlement) -- must NOT flip
        is_active to False immediately, that would bypass the grace period.
        """
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="pro_monthly", status="active", is_active=True)
        service, _ = make_service(sub)

        service.handle_webhook_event("subscription.halted", {"notes": {"finvigil_user_id": str(user_id)}})

        assert sub.status == "past_due"
        assert sub.is_active is True  # untouched -- grace period still applies

    def test_resumed_sets_active(self):
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="pro_monthly", status="past_due", is_active=True)
        service, _ = make_service(sub)

        service.handle_webhook_event("subscription.resumed", {"notes": {"finvigil_user_id": str(user_id)}})

        assert sub.status == "active"
        assert sub.is_active is True

    def test_missing_finvigil_user_id_raises(self):
        service, _ = make_service()
        with pytest.raises(ValueError, match="finvigil_user_id"):
            service.handle_webhook_event("subscription.activated", {"notes": {}})

    def test_invalid_uuid_in_notes_raises(self):
        service, _ = make_service()
        with pytest.raises(ValueError, match="not a valid UUID"):
            service.handle_webhook_event(
                "subscription.activated", {"notes": {"finvigil_user_id": "not-a-uuid"}}
            )

    def test_unrecognized_event_type_is_silently_ignored(self):
        """An unmodeled-but-validly-signed event (invoice.*, payment.*,
        etc.) must not raise and must not change subscription state."""
        user_id = uuid4()
        sub = FakeSubscription(user_id=user_id, plan_id="pro_monthly", status="active")
        service, _ = make_service(sub)

        service.handle_webhook_event("invoice.paid", {"notes": {"finvigil_user_id": str(user_id)}})

        assert sub.status == "active"
        assert sub.plan_id == "pro_monthly"


class TestCreateSubscriptionValidation:
    def test_invalid_finvigil_plan_id_rejected(self):
        service, _ = make_service(FakeSubscription())
        with pytest.raises(ValueError, match="Invalid plan_id"):
            service.create_subscription(uuid4(), "not_a_real_plan")

    def test_unconfigured_razorpay_plan_raises_runtime_error(self, monkeypatch):
        """If an admin hasn't set the matching RAZORPAY_PLAN_* env var,
        this must fail loudly (RuntimeError) rather than silently create a
        Razorpay subscription with a garbage/empty plan_id."""
        import app.core.razorpay_client as razorpay_client_module

        monkeypatch.setattr(razorpay_client_module, "get_razorpay_plan_id", lambda finvigil_plan_id: None)
        service, _ = make_service(FakeSubscription())

        with pytest.raises(RuntimeError, match="not configured"):
            service.create_subscription(uuid4(), "pro_monthly")


class TestRazorpayPlanIdMappingLive:
    """
    Live verification against Razorpay's real API (network required) that
    each FinVigil tier maps to a plan Razorpay itself reports as having
    the CORRECT name/price/period -- exactly the class of bug found and
    fixed earlier today (all 4 plan IDs were distinct and non-empty, just
    assigned to the wrong tier). Distinctness alone is not sufficient
    verification, which is why this checks Razorpay's own reported
    name/amount for each, not just "the 4 values differ".
    """

    # Razorpay's plan API uses "period" for the unit (monthly/yearly) and
    # "interval" for the numeric multiplier (e.g. interval=1 -> every 1
    # period) -- these are easy to swap by mistake, confirmed the hard way
    # below before fixing this test.
    EXPECTED = {
        "RAZORPAY_PLAN_PRO_MONTHLY": {"amount_rupees": 299, "period": "monthly"},
        "RAZORPAY_PLAN_PRO_ANNUAL": {"amount_rupees": 2499, "period": "yearly"},
        "RAZORPAY_PLAN_PREMIUM_MONTHLY": {"amount_rupees": 799, "period": "monthly"},
        "RAZORPAY_PLAN_PREMIUM_ANNUAL": {"amount_rupees": 6999, "period": "yearly"},
    }

    def test_each_plan_id_matches_its_expected_price_and_period(self):
        import requests
        from dotenv import dotenv_values

        env = dotenv_values(r"C:\Users\tejas\OneDrive\Desktop\finvigil-ai\backend\.env")
        key_id = env["RAZORPAY_KEY_ID"]
        key_secret = env["RAZORPAY_KEY_SECRET"]

        plan_ids_by_var = {var: env[var] for var in self.EXPECTED}
        # No two FinVigil tiers may point at the same Razorpay plan --
        # necessary but NOT sufficient (today's bug had 4 distinct values,
        # just in the wrong slots).
        assert len(set(plan_ids_by_var.values())) == 4, "Two or more tiers share the same Razorpay plan ID"

        for var_name, expected in self.EXPECTED.items():
            plan_id = plan_ids_by_var[var_name]
            resp = requests.get(
                f"https://api.razorpay.com/v1/plans/{plan_id}",
                auth=(key_id, key_secret), timeout=10,
            )
            assert resp.status_code == 200, f"{var_name} ({plan_id}): Razorpay lookup failed"
            data = resp.json()
            actual_amount = data["item"]["amount"] / 100
            actual_period = data["period"]

            assert actual_amount == expected["amount_rupees"], (
                f"{var_name} ({plan_id}) is priced Rs.{actual_amount} on Razorpay, "
                f"expected Rs.{expected['amount_rupees']}"
            )
            assert actual_period == expected["period"], (
                f"{var_name} ({plan_id}) has period '{actual_period}', "
                f"expected '{expected['period']}'"
            )

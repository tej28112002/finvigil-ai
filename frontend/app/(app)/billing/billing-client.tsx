"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api";

interface SubscriptionResponse {
  plan_id: string;
  status: string;
  is_active: boolean;
  current_period_end: string | null;
  is_pro_or_premium: boolean;
  in_grace_period: boolean;
  grace_deadline: string | null;
}

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  pro_monthly: "Pro — Monthly",
  pro_annual: "Pro — Annual",
  premium_monthly: "Premium — Monthly",
  premium_annual: "Premium — Annual",
};

const PLAN_PRICES: Record<string, string> = {
  pro_monthly: "₹299/mo",
  pro_annual: "₹2,499/yr",
  premium_monthly: "₹799/mo",
  premium_annual: "₹6,999/yr",
};

const UPGRADE_PLANS = ["pro_monthly", "pro_annual", "premium_monthly", "premium_annual"];

function statusTone(status: string): "gain" | "loss" | "neutral" | "estimate" {
  if (status === "active") return "gain";
  if (status === "past_due") return "loss";
  if (status === "grace") return "estimate";
  return "neutral"; // canceled
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function BillingClient() {
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgradingPlan, setUpgradingPlan] = useState<string | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  async function loadSubscription() {
    setLoading(true);
    setError(null);
    try {
      const sub = await apiFetch<SubscriptionResponse>("/billing/subscription");
      setSubscription(sub);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your subscription.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSubscription();
  }, []);

  async function handleUpgrade(planId: string) {
    setUpgradingPlan(planId);
    setError(null);
    try {
      const result = await apiFetch<{ checkout_url: string | null }>(
        "/billing/create-subscription",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plan_id: planId }),
        }
      );
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else {
        setError("Subscription created, but no checkout link was returned. Contact support.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError(
          "Billing isn't fully configured yet — this plan hasn't been set up in Razorpay. Try again later or contact support."
        );
      } else {
        setError(err instanceof Error ? err.message : "Could not start checkout.");
      }
    } finally {
      setUpgradingPlan(null);
    }
  }

  async function handleCancel() {
    setCanceling(true);
    setError(null);
    try {
      const sub = await apiFetch<SubscriptionResponse>("/billing/cancel-subscription", {
        method: "POST",
      });
      setSubscription(sub);
      setShowCancelConfirm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel subscription.");
    } finally {
      setCanceling(false);
    }
  }

  const canCancel =
    subscription &&
    subscription.plan_id !== "free" &&
    subscription.status !== "canceled";

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="mb-1">
        <h1 className="font-display text-2xl text-ink">Billing</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Manage your FinVigil plan and subscription.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-ink-faint">Loading…</p>
      ) : subscription ? (
        <>
          {/* Current plan card */}
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <MetricLabel>Current plan</MetricLabel>
              <Badge tone={statusTone(subscription.status)}>{subscription.status}</Badge>
            </div>
            <div className="mt-3 font-display text-xl text-ink">
              {PLAN_LABELS[subscription.plan_id] ?? subscription.plan_id}
            </div>
            {subscription.current_period_end && (
              <p className="mt-1 text-sm text-ink-muted">
                Next billing date: {fmtDate(subscription.current_period_end)}
              </p>
            )}
            {subscription.in_grace_period && subscription.grace_deadline && (
              <div className="mt-3 rounded-md border border-loss/30 bg-loss-soft px-3 py-2 text-xs text-loss">
                Your last payment failed. You still have full access until{" "}
                {fmtDate(subscription.grace_deadline)} — update your payment method
                before then to avoid being downgraded to Free.
              </div>
            )}
          </Card>

          {error && (
            <div className="rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
              {error}
            </div>
          )}

          {/* Upgrade options */}
          {!subscription.is_pro_or_premium && (
            <Card className="p-5">
              <MetricLabel>Upgrade to Pro or Premium</MetricLabel>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {UPGRADE_PLANS.map((planId) => (
                  <div
                    key={planId}
                    className="flex items-center justify-between rounded-md border border-rule px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">{PLAN_LABELS[planId]}</p>
                      <p className="text-xs text-ink-faint">{PLAN_PRICES[planId]}</p>
                    </div>
                    <Button
                      onClick={() => handleUpgrade(planId)}
                      loading={upgradingPlan === planId}
                      className="h-7 px-3 text-xs"
                    >
                      Upgrade
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Cancel */}
          {canCancel && (
            <Card className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <MetricLabel>Cancel subscription</MetricLabel>
                  <p className="mt-1 text-sm text-ink-muted">
                    You&apos;ll lose Pro/Premium access at the end of your current period.
                  </p>
                </div>
                {!showCancelConfirm ? (
                  <button
                    type="button"
                    onClick={() => setShowCancelConfirm(true)}
                    className="cursor-pointer rounded-md border border-rule px-3 py-1.5 text-sm font-medium text-loss transition-colors hover:bg-loss-soft"
                  >
                    Cancel plan
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      onClick={() => setShowCancelConfirm(false)}
                      className="h-8 px-3 text-xs"
                    >
                      Keep plan
                    </Button>
                    <button
                      type="button"
                      onClick={handleCancel}
                      disabled={canceling}
                      className="cursor-pointer rounded-md bg-loss px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                    >
                      {canceling ? "Canceling…" : "Confirm cancel"}
                    </button>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Payment history */}
          <Card className="p-5 opacity-60">
            <div className="flex items-center justify-between">
              <MetricLabel>Payment history</MetricLabel>
              <Badge tone="neutral">Not available yet</Badge>
            </div>
            <p className="mt-1 text-sm text-ink-muted">
              Invoice and payment records aren&apos;t tracked yet — check your Razorpay receipts by email for now.
            </p>
          </Card>
        </>
      ) : (
        error && (
          <div className="rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )
      )}
    </div>
  );
}

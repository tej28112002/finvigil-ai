"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { apiFetch, ApiError } from "@/lib/api";

interface BrokerConnectionSummary {
  id: string;
  broker_name: string;
  status: string;
}

interface DashboardSummary {
  total_equity_value: string;
  total_crypto_value: string;
  day_pnl: string;
  unrealized_pnl: string;
}

interface ImpersonateView {
  user_id: string;
  email: string | null;
  created_at: string | null;
  role: string;
  plan_id: string;
  subscription_status: string;
  broker_connections: BrokerConnectionSummary[];
  dashboard_summary: DashboardSummary | null;
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function UserDetailClient({ userId }: { userId: string }) {
  const [view, setView] = useState<ImpersonateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resyncingId, setResyncingId] = useState<string | null>(null);
  const [resyncResult, setResyncResult] = useState<string | null>(null);

  async function loadView() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ImpersonateView>(`/admin/users/${userId}/impersonate-view`);
      setView(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Admin or support access required to view this page.");
      } else {
        setError(err instanceof Error ? err.message : "Could not load user.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadView();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function handleResync(brokerConnectionId: string) {
    setResyncingId(brokerConnectionId);
    setResyncResult(null);
    try {
      const result = await apiFetch<{ imported: number; skipped: number; errors: string[] }>(
        `/admin/users/${userId}/impersonate-view/resync-broker/${brokerConnectionId}`,
        { method: "POST" }
      );
      setResyncResult(`Imported ${result.imported}, skipped ${result.skipped}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resync failed.");
    } finally {
      setResyncingId(null);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-3xl"><p className="text-sm text-ink-faint">Loading…</p></div>;
  }

  if (error && !view) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">{error}</div>
      </div>
    );
  }

  if (!view) return null;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex items-center gap-2">
        <Badge tone="estimate">Support view — read-only</Badge>
        <p className="text-xs text-ink-faint">
          This is a read-only summary; you are not signed in as this user. Every view is logged.
        </p>
      </div>

      <Card className="p-5">
        <MetricLabel>User</MetricLabel>
        <h1 className="font-display mt-1 text-xl text-ink">{view.email ?? "—"}</h1>
        <p className="mt-1 text-sm text-ink-muted">Joined {fmtDate(view.created_at)}</p>
        <div className="mt-3 flex gap-2">
          <Badge tone="brand">{view.role}</Badge>
          <Badge tone="neutral">{view.plan_id}</Badge>
          <Badge tone={view.subscription_status === "active" ? "gain" : "loss"}>
            {view.subscription_status}
          </Badge>
        </div>
      </Card>

      {view.dashboard_summary && (
        <div className="mt-4 grid grid-cols-2 gap-4">
          <Card className="p-5">
            <MetricLabel>Equity value</MetricLabel>
            <div className="mt-3"><Money value={view.dashboard_summary.total_equity_value} size="lg" /></div>
          </Card>
          <Card className="p-5">
            <MetricLabel>Crypto value</MetricLabel>
            <div className="mt-3"><Money value={view.dashboard_summary.total_crypto_value} size="lg" /></div>
          </Card>
          <Card className="p-5">
            <MetricLabel>Day P&amp;L</MetricLabel>
            <div className="mt-3"><Money value={view.dashboard_summary.day_pnl} size="lg" tone="auto" signed /></div>
          </Card>
          <Card className="p-5">
            <MetricLabel>Unrealized P&amp;L</MetricLabel>
            <div className="mt-3"><Money value={view.dashboard_summary.unrealized_pnl} size="lg" tone="auto" signed /></div>
          </Card>
        </div>
      )}

      <div className="mt-6">
        <h2 className="mb-2 font-display text-lg text-ink">Broker connections</h2>
        {view.broker_connections.length === 0 ? (
          <p className="text-sm text-ink-faint">No broker connections.</p>
        ) : (
          <div className="space-y-2">
            {view.broker_connections.map((bc) => (
              <Card key={bc.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium text-ink">{bc.broker_name}</p>
                  <Badge tone={bc.status === "active" ? "gain" : "neutral"}>{bc.status}</Badge>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => handleResync(bc.id)}
                  loading={resyncingId === bc.id}
                  className="h-8 px-3 text-xs"
                >
                  Resync
                </Button>
              </Card>
            ))}
          </div>
        )}
        {resyncResult && (
          <p className="mt-2 text-xs text-ink-muted">{resyncResult}</p>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}
    </div>
  );
}

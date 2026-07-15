"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";

interface AdminUserSummary {
  user_id: string;
  email: string | null;
  role: string;
}

interface AuditLog {
  id: string;
  admin_user_id: string;
  target_user_id: string;
  action: string;
  created_at: string;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function actionLabel(action: string) {
  return action.replace(/_/g, " ");
}

export function AdminDashboardClient() {
  const [users, setUsers] = useState<AdminUserSummary[] | null>(null);
  const [logs, setLogs] = useState<AuditLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<AdminUserSummary[]>("/admin/users"),
      apiFetch<AuditLog[]>("/admin/audit-logs").catch(() => null), // audit log is admin-only; support role gets 403
    ])
      .then(([u, l]) => {
        setUsers(u);
        setLogs(l);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load admin data."));
  }, []);

  const adminCount = users?.filter((u) => u.role === "admin").length ?? 0;
  const supportCount = users?.filter((u) => u.role === "support").length ?? 0;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Admin</h1>
        <p className="mt-1 text-sm text-ink-muted">
          User management, feature flags, and ITR schema mappings.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <MetricLabel>Total users</MetricLabel>
          <div className="mt-3 font-mono text-2xl font-medium text-ink">
            {users?.length ?? "—"}
          </div>
        </Card>
        <Card className="p-5">
          <MetricLabel>Admins</MetricLabel>
          <div className="mt-3 font-mono text-2xl font-medium text-ink">{adminCount}</div>
        </Card>
        <Card className="p-5">
          <MetricLabel>Support</MetricLabel>
          <div className="mt-3 font-mono text-2xl font-medium text-ink">{supportCount}</div>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Link href="/admin/users">
          <Card interactive className="p-5">
            <h3 className="font-display text-base text-ink">User management</h3>
            <p className="mt-1.5 text-sm text-ink-muted">
              List users, view subscriptions, toggle roles, and open a read-only support view.
            </p>
          </Card>
        </Link>
        <Link href="/admin/feature-flags">
          <Card interactive className="p-5">
            <h3 className="font-display text-base text-ink">Feature flags</h3>
            <p className="mt-1.5 text-sm text-ink-muted">
              Global defaults and per-user overrides for gating features.
            </p>
          </Card>
        </Link>
        <Link href="/admin/itr-schemas">
          <Card interactive className="p-5">
            <h3 className="font-display text-base text-ink">ITR-3 schemas</h3>
            <p className="mt-1.5 text-sm text-ink-muted">
              Upload each year's CBDT field-name mapping — no code deploy needed.
            </p>
          </Card>
        </Link>
      </div>

      {logs && logs.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-2 font-display text-lg text-ink">Recent activity</h2>
          <Card className="divide-y divide-rule p-0">
            {logs.slice(0, 10).map((log) => (
              <div key={log.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  <Badge tone="neutral">{actionLabel(log.action)}</Badge>
                  <span className="text-xs text-ink-faint">
                    target: {log.target_user_id.slice(0, 8)}…
                  </span>
                </div>
                <span className="text-xs text-ink-faint">{fmtDate(log.created_at)}</span>
              </div>
            ))}
          </Card>
        </div>
      )}
    </div>
  );
}

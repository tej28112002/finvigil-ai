"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetch } from "@/lib/api";

interface AdminUserSummary {
  user_id: string;
  email: string | null;
  created_at: string | null;
  role: string;
  plan_id: string;
  subscription_status: string;
}

const ROLES = ["user", "support", "admin"] as const;

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function roleTone(role: string): "brand" | "estimate" | "neutral" {
  if (role === "admin") return "brand";
  if (role === "support") return "estimate";
  return "neutral";
}

function statusTone(status: string): "gain" | "loss" | "neutral" {
  if (status === "active") return "gain";
  if (status === "past_due" || status === "canceled") return "loss";
  return "neutral";
}

export function UsersClient() {
  const [users, setUsers] = useState<AdminUserSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  async function loadUsers() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AdminUserSummary[]>("/admin/users");
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleRoleChange(userId: string, role: string) {
    setUpdatingId(userId);
    setError(null);
    try {
      await apiFetch(`/admin/users/${userId}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update role.");
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">User management</h1>
        <p className="mt-1 text-sm text-ink-muted">
          {users ? `${users.length} user${users.length === 1 ? "" : "s"}` : "Loading…"}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-ink-faint">Loading…</p>
      ) : !users || users.length === 0 ? (
        <EmptyState title="No users found" description="No user accounts exist yet." />
      ) : (
        <Table>
          <THead>
            <Th>Email</Th>
            <Th>Joined</Th>
            <Th>Plan</Th>
            <Th>Subscription</Th>
            <Th>Role</Th>
            <Th align="right">Action</Th>
          </THead>
          <tbody>
            {users.map((u) => (
              <Tr key={u.user_id}>
                <Td className="font-medium">{u.email ?? "—"}</Td>
                <Td className="text-ink-muted">{fmtDate(u.created_at)}</Td>
                <Td className="font-mono text-xs">{u.plan_id}</Td>
                <Td>
                  <Badge tone={statusTone(u.subscription_status)}>{u.subscription_status}</Badge>
                </Td>
                <Td>
                  <select
                    value={u.role}
                    disabled={updatingId === u.user_id}
                    onChange={(e) => handleRoleChange(u.user_id, e.target.value)}
                    className="h-7 rounded border border-rule bg-surface px-2 text-xs text-ink disabled:opacity-50"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                  <span className="ml-2">
                    <Badge tone={roleTone(u.role)}>{u.role}</Badge>
                  </span>
                </Td>
                <Td align="right">
                  <Link href={`/admin/users/${u.user_id}`}>
                    <Button variant="secondary" className="h-7 px-3 text-xs">
                      View
                    </Button>
                  </Link>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

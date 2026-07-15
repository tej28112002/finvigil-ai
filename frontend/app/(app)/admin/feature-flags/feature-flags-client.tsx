"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetch } from "@/lib/api";

interface FeatureFlag {
  id: string;
  flag_key: string;
  user_id: string | null;
  is_enabled: boolean;
  description: string | null;
}

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

export function FeatureFlagsClient() {
  const [flags, setFlags] = useState<FeatureFlag[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [flagKey, setFlagKey] = useState("");
  const [description, setDescription] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [isEnabled, setIsEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function loadFlags() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<FeatureFlag[]>("/admin/feature-flags");
      setFlags(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load feature flags.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFlags();
  }, []);

  async function handleToggle(flag: FeatureFlag) {
    setTogglingId(flag.id);
    try {
      await apiFetch("/admin/feature-flags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flag_key: flag.flag_key,
          is_enabled: !flag.is_enabled,
          description: flag.description,
          target_user_id: flag.user_id,
        }),
      });
      await loadFlags();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not toggle flag.");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleSubmit() {
    setFormError(null);
    if (!flagKey.trim()) {
      setFormError("Flag key is required (e.g. monte_carlo_beta).");
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/admin/feature-flags", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flag_key: flagKey.trim(),
          is_enabled: isEnabled,
          description: description.trim() || null,
          target_user_id: targetUserId.trim() || null,
        }),
      });
      setShowForm(false);
      setFlagKey("");
      setDescription("");
      setTargetUserId("");
      setIsEnabled(true);
      await loadFlags();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save flag.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">Feature flags</h1>
          <p className="mt-1 text-sm text-ink-muted">
            A flag with no user is the global default; a flag scoped to a user ID overrides it for that user only.
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "New flag"}</Button>
      </div>

      {showForm && (
        <Card className="mb-6 p-5">
          <div className="space-y-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
                Flag key
              </label>
              <input className={inputCls} placeholder="monte_carlo_beta" value={flagKey} onChange={(e) => setFlagKey(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
                Description
              </label>
              <input className={inputCls} placeholder="What this flag gates" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
                Target user ID
              </label>
              <input className={inputCls} placeholder="Leave blank for global default" value={targetUserId} onChange={(e) => setTargetUserId(e.target.value)} />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={isEnabled} onChange={(e) => setIsEnabled(e.target.checked)} className="cursor-pointer" />
              <label className="text-sm text-ink">Enabled</label>
            </div>
          </div>

          {formError && (
            <div className="mt-3 rounded-md border border-loss/30 bg-loss-soft px-3 py-2 text-xs text-loss">{formError}</div>
          )}

          <div className="mt-4 flex justify-end">
            <Button onClick={handleSubmit} loading={submitting}>Save</Button>
          </div>
        </Card>
      )}

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-ink-faint">Loading…</p>
      ) : !flags || flags.length === 0 ? (
        <EmptyState title="No feature flags yet" description="Create one above to gate a feature globally or per-user." />
      ) : (
        <Table>
          <THead>
            <Th>Flag key</Th>
            <Th>Scope</Th>
            <Th>Description</Th>
            <Th>Status</Th>
            <Th align="right">Action</Th>
          </THead>
          <tbody>
            {flags.map((f) => (
              <Tr key={f.id}>
                <Td className="font-mono text-xs font-medium">{f.flag_key}</Td>
                <Td>
                  {f.user_id ? (
                    <span className="font-mono text-xs text-ink-muted">{f.user_id.slice(0, 8)}…</span>
                  ) : (
                    <Badge tone="brand">Global</Badge>
                  )}
                </Td>
                <Td className="text-ink-muted">{f.description ?? "—"}</Td>
                <Td>
                  <Badge tone={f.is_enabled ? "gain" : "neutral"}>{f.is_enabled ? "Enabled" : "Disabled"}</Badge>
                </Td>
                <Td align="right">
                  <Button
                    variant="secondary"
                    onClick={() => handleToggle(f)}
                    loading={togglingId === f.id}
                    className="h-7 px-3 text-xs"
                  >
                    {f.is_enabled ? "Disable" : "Enable"}
                  </Button>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

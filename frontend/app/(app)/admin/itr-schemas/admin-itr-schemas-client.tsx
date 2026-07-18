"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetch } from "@/lib/api";

interface ItrSchemaMapping {
  id: string;
  ay: string;
  schema_version: string;
  is_active: boolean;
  uploaded_at: string;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

export function AdminItrSchemasClient() {
  const [schemas, setSchemas] = useState<ItrSchemaMapping[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingAy, setTogglingAy] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [ay, setAy] = useState("");
  const [schemaVersion, setSchemaVersion] = useState("");
  const [mappingJson, setMappingJson] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function loadSchemas() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ItrSchemaMapping[]>("/admin/itr-schemas");
      setSchemas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load ITR schemas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    apiFetch<{ role: string }>("/me")
      .then((me) => setIsAdmin(me.role === "admin"))
      .catch(() => setIsAdmin(false));
    loadSchemas();
  }, []);

  async function handleToggleActive(mapping: ItrSchemaMapping) {
    setTogglingAy(mapping.ay);
    try {
      await apiFetch(`/admin/itr-schemas/${mapping.ay}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !mapping.is_active }),
      });
      await loadSchemas();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update schema.");
    } finally {
      setTogglingAy(null);
    }
  }

  async function handleSubmit() {
    setFormError(null);

    if (!ay.trim()) {
      setFormError("AY is required (e.g. 2027-28).");
      return;
    }
    if (!schemaVersion.trim()) {
      setFormError("Schema version is required (e.g. 1.0).");
      return;
    }

    let parsedMapping: unknown;
    try {
      parsedMapping = JSON.parse(mappingJson);
    } catch {
      setFormError("Mapping JSON is not valid JSON.");
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch("/admin/itr-schemas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ay: ay.trim(),
          schema_version: schemaVersion.trim(),
          mapping_json: parsedMapping,
        }),
      });
      setShowForm(false);
      setAy("");
      setSchemaVersion("");
      setMappingJson("");
      await loadSchemas();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">ITR-3 schema mappings</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Add a new assessment year&apos;s CBDT field-name mapping here — no code change or deploy needed.
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Upload New Schema"}
          </Button>
        )}
      </div>

      {isAdmin && showForm && (
        <Card className="mb-6 p-5">
          <h2 className="mb-4 font-display text-base text-ink">Upload schema mapping</h2>
          <div className="space-y-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
                AY
              </label>
              <input
                className={inputCls}
                placeholder="2027-28"
                value={ay}
                onChange={(e) => setAy(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
                Schema version
              </label>
              <input
                className={inputCls}
                placeholder="1.0"
                value={schemaVersion}
                onChange={(e) => setSchemaVersion(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium uppercase tracking-wider text-ink-muted">
                Mapping JSON
              </label>
              <textarea
                className={`${inputCls} h-64 font-mono text-xs leading-relaxed`}
                placeholder='{"ay": "2027-28", "schema_version": "1.0", ...}'
                value={mappingJson}
                onChange={(e) => setMappingJson(e.target.value)}
              />
            </div>
          </div>

          {formError && (
            <div className="mt-3 rounded-md border border-loss/30 bg-loss-soft px-3 py-2 text-xs text-loss">
              {formError}
            </div>
          )}

          <div className="mt-4 flex justify-end">
            <Button onClick={handleSubmit} loading={submitting}>
              Submit
            </Button>
          </div>
        </Card>
      )}

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-ink-faint">Loading…</p>
      ) : !schemas || schemas.length === 0 ? (
        <EmptyState
          title="No ITR schema mappings yet"
          description="Upload the current assessment year's CBDT field-name mapping to enable ITR-3 export for users."
        />
      ) : (
        <Table>
          <THead>
            <Th>AY</Th>
            <Th>Version</Th>
            <Th>Active</Th>
            <Th>Uploaded</Th>
            <Th align="right">Action</Th>
          </THead>
          <tbody>
            {schemas.map((s) => (
              <Tr key={s.id}>
                <Td className="font-medium">{s.ay}</Td>
                <Td className="font-mono">{s.schema_version}</Td>
                <Td>
                  <Badge tone={s.is_active ? "gain" : "neutral"}>
                    {s.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Td>
                <Td className="text-ink-muted">{fmtDate(s.uploaded_at)}</Td>
                <Td align="right">
                  {isAdmin && (
                    <Button
                      variant="secondary"
                      onClick={() => handleToggleActive(s)}
                      loading={togglingAy === s.ay}
                      className="h-7 px-3 text-xs"
                    >
                      {s.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

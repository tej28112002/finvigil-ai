"use client";

import { useEffect, useState } from "react";
import { AYSelector } from "@/components/ui/ay-selector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { DEFAULT_AY } from "@/lib/ay";
import { apiFetch, ApiError } from "@/lib/api";

// ── types ────────────────────────────────────────────────────────────────────

interface AisUpload {
  id: string;
  assessment_year: string;
  version: number;
  is_latest: boolean;
  upload_date: string;
  created_at: string;
}

interface AisLine {
  id: string;
  section_code: string;
  description: string | null;
  reported_amount: string | null;
}

interface AisMatchResult {
  id: string;
  ais_line_id: string;
  match_status: "matched" | "mismatch" | "unresolved";
  mismatch_type: string | null;
  resolution_notes: string | null;
}

interface AisLineWithMatch {
  line: AisLine;
  match_result: AisMatchResult | null;
}

interface AisUploadSummary {
  upload: AisUpload;
  total_lines: number;
  matched_count: number;
  mismatch_count: number;
  unresolved_count: number;
  match_percentage: string;
}

interface AisUploadDetail {
  summary: AisUploadSummary;
  lines: AisLineWithMatch[];
  disclaimer: string;
}

interface AisUploadHistory {
  assessment_year: string;
  versions: AisUploadSummary[];
}

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusTone(status: string): "gain" | "loss" | "estimate" {
  if (status === "matched") return "gain";
  if (status === "mismatch") return "loss";
  return "estimate";
}

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

// ── main component ────────────────────────────────────────────────────────────

export function AisClient() {
  const [ay, setAy] = useState(DEFAULT_AY);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [history, setHistory] = useState<AisUploadHistory | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [detail, setDetail] = useState<AisUploadDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [mismatchOnly, setMismatchOnly] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [bulkResolving, setBulkResolving] = useState(false);

  async function loadHistory(targetAy: string) {
    setLoadingHistory(true);
    setError(null);
    try {
      const h = await apiFetch<AisUploadHistory>(
        `/ais/uploads/${targetAy}/history`
      );
      setHistory(h);
      const latest = h.versions.find((v) => v.upload.is_latest) ?? h.versions[0];
      if (latest) {
        await loadDetail(latest.upload.id);
      } else {
        setDetail(null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setHistory({ assessment_year: targetAy, versions: [] });
        setDetail(null);
      } else {
        setError(err instanceof Error ? err.message : "Could not load AIS history.");
      }
    } finally {
      setLoadingHistory(false);
    }
  }

  async function loadDetail(uploadId: string) {
    setLoadingDetail(true);
    try {
      const d = await apiFetch<AisUploadDetail>(`/ais/uploads/${uploadId}`);
      setDetail(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load upload detail.");
    } finally {
      setLoadingDetail(false);
    }
  }

  useEffect(() => {
    loadHistory(ay);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ay]);

  async function handleUpload() {
    if (!file) {
      setError("Choose a .json or .csv AIS file first.");
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const d = await apiFetch<AisUploadDetail>(
        `/ais/upload?assessment_year=${encodeURIComponent(ay)}`,
        { method: "POST", body: formData }
      );
      setDetail(d);
      setFile(null);
      await loadHistory(ay);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Check the file format.");
    } finally {
      setUploading(false);
    }
  }

  async function handleResolve(matchResultId: string) {
    setResolvingId(matchResultId);
    try {
      await apiFetch(`/ais/match-results/${matchResultId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution_notes: "Reviewed manually — confirmed." }),
      });
      if (detail) await loadDetail(detail.summary.upload.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save resolution.");
    } finally {
      setResolvingId(null);
    }
  }

  async function handleBulkResolveExact() {
    if (!detail) return;
    setBulkResolving(true);
    try {
      await apiFetch(`/ais/uploads/${detail.summary.upload.id}/bulk-resolve-exact`, {
        method: "POST",
      });
      await loadDetail(detail.summary.upload.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk resolve failed.");
    } finally {
      setBulkResolving(false);
    }
  }

  const displayLines = detail
    ? mismatchOnly
      ? detail.lines.filter(
          (l) => l.match_result?.match_status === "mismatch" || l.match_result?.match_status === "unresolved"
        )
      : detail.lines
    : [];

  return (
    <div className="mx-auto max-w-5xl">
      {/* Page header */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">AIS Reconciliation</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Upload your Annual Information Statement and compare it against what FinVigil computed from your trades.
          </p>
        </div>
        <AYSelector value={ay} onChange={setAy} />
      </div>

      {/* ── Upload card ── */}
      <Card className="p-5">
        <h2 className="mb-4 font-display text-base text-ink">Upload AIS</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="file"
            accept=".json,.csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className={`${inputCls} flex-1 cursor-pointer file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-brand-soft file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-brand`}
          />
          <Button onClick={handleUpload} loading={uploading}>
            {uploading ? "Uploading…" : "Upload & Match"}
          </Button>
        </div>
        <p className="mt-2 text-xs text-ink-faint">
          Accepts .json or .csv. Each upload creates a new version for AY {ay} — your previous versions stay in history.
        </p>
        {error && (
          <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )}
      </Card>

      {/* ── Version history ── */}
      {history && history.versions.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-2 font-display text-lg text-ink">Version history — AY {ay}</h2>
          <Table>
            <THead>
              <Th>Version</Th>
              <Th>Uploaded</Th>
              <Th align="right">Lines</Th>
              <Th align="right">Match %</Th>
              <Th>Status</Th>
            </THead>
            <tbody>
              {history.versions.map((v) => (
                <Tr
                  key={v.upload.id}
                  className={`cursor-pointer hover:bg-bg ${detail?.summary.upload.id === v.upload.id ? "bg-bg" : ""}`}
                >
                  <Td className="font-medium" >
                    <button
                      type="button"
                      onClick={() => loadDetail(v.upload.id)}
                      className="cursor-pointer text-left hover:underline"
                    >
                      v{v.upload.version}
                    </button>
                  </Td>
                  <Td className="text-ink-muted">{fmtDate(v.upload.upload_date)}</Td>
                  <Td align="right" className="font-mono">{v.total_lines}</Td>
                  <Td align="right" className="font-mono">{v.match_percentage}%</Td>
                  <Td>
                    {v.upload.is_latest && <Badge tone="brand">Latest</Badge>}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {/* ── Loading state ── */}
      {(loadingHistory || loadingDetail) && !detail && (
        <p className="mt-6 text-sm text-ink-faint">Loading…</p>
      )}

      {/* ── No uploads yet ── */}
      {!loadingHistory && history && history.versions.length === 0 && (
        <div className="mt-6">
          <EmptyState
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" />
                <path d="M14 2v6h6" />
              </svg>
            }
            title={`No AIS uploaded yet for AY ${ay}`}
            description="Upload your Annual Information Statement (JSON or CSV export from the income-tax portal) to reconcile it against your FinVigil trade data."
          />
        </div>
      )}

      {/* ── Resolution grid ── */}
      {detail && (
        <div className="mt-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-lg text-ink">
              Resolution grid — v{detail.summary.upload.version}
            </h2>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-xs text-ink-muted">
                <input
                  type="checkbox"
                  checked={mismatchOnly}
                  onChange={(e) => setMismatchOnly(e.target.checked)}
                  className="cursor-pointer"
                />
                Mismatches only
              </label>
              <Button
                variant="secondary"
                onClick={handleBulkResolveExact}
                loading={bulkResolving}
                className="h-8 px-3 text-xs"
              >
                Bulk-confirm exact matches
              </Button>
            </div>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <Card className="p-5">
              <MetricLabel>Total lines</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-ink">
                {detail.summary.total_lines}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Matched</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-gain">
                {detail.summary.matched_count}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Mismatched</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-loss">
                {detail.summary.mismatch_count}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Unresolved</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-estimate">
                {detail.summary.unresolved_count}
              </div>
              <p className="mt-1 text-xs text-ink-faint">{detail.summary.match_percentage}% match rate</p>
            </Card>
          </div>

          {/* Lines table */}
          <div className="mt-6">
            {displayLines.length === 0 ? (
              <EmptyState
                title="No mismatches"
                description="Every line in this upload matched FinVigil's computed data, or no lines exist to show."
              />
            ) : (
              <Table>
                <THead>
                  <Th>Section</Th>
                  <Th>Description</Th>
                  <Th align="right">Reported amount</Th>
                  <Th>Status</Th>
                  <Th>Type</Th>
                  <Th>Notes</Th>
                  <Th align="right">Action</Th>
                </THead>
                <tbody>
                  {displayLines.map(({ line, match_result }) => (
                    <Tr key={line.id}>
                      <Td className="font-medium">{line.section_code}</Td>
                      <Td className="max-w-[16rem] truncate text-ink-muted">
                        <span title={line.description ?? undefined}>{line.description ?? "—"}</span>
                      </Td>
                      <Td align="right">
                        {line.reported_amount !== null ? (
                          <Money value={line.reported_amount} size="sm" />
                        ) : (
                          "—"
                        )}
                      </Td>
                      <Td>
                        {match_result ? (
                          <Badge tone={statusTone(match_result.match_status)}>
                            {match_result.match_status}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </Td>
                      <Td className="text-ink-muted">{match_result?.mismatch_type ?? "—"}</Td>
                      <Td className="max-w-[14rem] truncate text-xs text-ink-faint">
                        <span title={match_result?.resolution_notes ?? undefined}>
                          {match_result?.resolution_notes ?? "—"}
                        </span>
                      </Td>
                      <Td align="right">
                        {match_result && match_result.match_status !== "matched" && !match_result.resolution_notes && (
                          <Button
                            variant="secondary"
                            onClick={() => handleResolve(match_result.id)}
                            loading={resolvingId === match_result.id}
                            className="h-7 px-2.5 text-xs"
                          >
                            Resolve
                          </Button>
                        )}
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>

          {/* Disclaimer */}
          <Card className="mt-4 p-4">
            <p className="flex items-start gap-2 text-xs text-ink-muted">
              <Badge tone="estimate">Not financial advice</Badge>
              <span>{detail.disclaimer}</span>
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}

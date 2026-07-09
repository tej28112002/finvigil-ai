"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

interface BrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}

interface DashboardTotals {
  total_equity_value: string;
  total_crypto_value: string;
}

interface PortfolioItem {
  instrument_id: string;
}

interface CsvImportResult {
  total_rows: number;
  imported: number;
  skipped: number;
  errors: string[];
}

const LAST_SYNCED_KEY = "finvigil-last-synced-zerodha";

function readLastSynced(): string | null {
  try {
    return window.localStorage.getItem(LAST_SYNCED_KEY);
  } catch {
    return null;
  }
}

function writeLastSynced() {
  try {
    window.localStorage.setItem(LAST_SYNCED_KEY, new Date().toISOString());
  } catch {
    // non-fatal — just a display nicety
  }
}

export default function BrokersPage() {
  const [brokers, setBrokers] = useState<BrokerConnection[] | null>(null);
  const [portfolioValue, setPortfolioValue] = useState<string | null>(null);
  const [holdingsCount, setHoldingsCount] = useState<number | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<CsvImportResult | null>(null);
  const [lastSynced, setLastSynced] = useState<string | null>(null);

  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectStep, setReconnectStep] = useState(false);

  const [inProgressNotice, setInProgressNotice] = useState<string | null>(null);

  const [csvUploading, setCsvUploading] = useState(false);
  const [csvResult, setCsvResult] = useState<CsvImportResult | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setUserId(session?.user.id ?? null);

      const [brokerList, dashboard, portfolio] = await Promise.all([
        apiFetch<BrokerConnection[]>("/brokers/"),
        apiFetch<DashboardTotals>("/dashboard/"),
        apiFetch<PortfolioItem[]>("/portfolio/"),
      ]);
      setBrokers(brokerList);
      setPortfolioValue(dashboard.total_equity_value);
      setHoldingsCount(portfolio.length);
      setLastSynced(readLastSynced());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load brokers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const zerodha = brokers?.find((b) => b.broker_name === "zerodha") ?? null;
  const csvConn = brokers?.find((b) => b.broker_name === "csv") ?? null;

  async function handleSyncNow() {
    if (!zerodha) return;
    setSyncing(true);
    setSyncResult(null);
    setError(null);
    try {
      const result = await apiFetch<CsvImportResult>(
        `/brokers/zerodha/sync?broker_connection_id=${zerodha.id}`,
        { method: "POST" }
      );
      setSyncResult(result);
      writeLastSynced();
      setLastSynced(readLastSynced());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function handleReconnect() {
    setReconnecting(true);
    setError(null);
    try {
      const { login_url } = await apiFetch<{ login_url: string }>(
        "/brokers/zerodha/login"
      );
      window.open(login_url, "_blank", "noopener,noreferrer");
      setReconnectStep(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start reconnect");
    } finally {
      setReconnecting(false);
    }
  }

  async function ensureCsvConnection(): Promise<string> {
    if (csvConn) return csvConn.id;
    const created = await apiFetch<BrokerConnection>("/brokers/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker_name: "csv" }),
    });
    setBrokers((prev) => (prev ? [...prev, created] : [created]));
    return created.id;
  }

  async function handleCsvUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setCsvUploading(true);
    setCsvError(null);
    setCsvResult(null);
    try {
      const brokerConnectionId = await ensureCsvConnection();
      const formData = new FormData();
      formData.append("file", file);
      const result = await apiFetch<CsvImportResult>(
        `/csv-import/tradebook?broker_connection_id=${brokerConnectionId}`,
        { method: "POST", body: formData }
      );
      setCsvResult(result);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setCsvError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setCsvUploading(false);
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" role="status" aria-label="Loading brokers">
        {[0, 1, 2].map((i) => (
          <Card key={i} className="h-32 animate-pulse p-5">
            <div className="h-3 w-24 rounded bg-rule" />
          </Card>
        ))}
      </div>
    );
  }

  if (error && !brokers) {
    return (
      <Card className="mx-auto max-w-md p-8 text-center">
        <p className="text-sm font-medium text-ink">Couldn&apos;t load brokers</p>
        <p className="mt-1 text-sm text-ink-muted">{error}</p>
        <Button onClick={load} className="mt-4">
          Try again
        </Button>
      </Card>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {error && (
        <Card className="p-4">
          <p className="text-sm text-loss" role="alert">{error}</p>
        </Card>
      )}

      {/* Zerodha */}
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{
                backgroundColor: zerodha?.status === "active" ? "var(--gain)" : "var(--ink-faint)",
              }}
              aria-hidden="true"
            />
            <div>
              <p className="font-medium" style={{ color: "var(--color-broker-zerodha)" }}>
                Zerodha
              </p>
              <p className="text-xs text-ink-muted">
                {zerodha
                  ? zerodha.status === "active"
                    ? "Connected"
                    : zerodha.status
                  : "Not connected"}
                {lastSynced && zerodha && (
                  <> · Last synced {new Date(lastSynced).toLocaleString("en-IN")}</>
                )}
              </p>
            </div>
          </div>

          {zerodha ? (
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleReconnect} loading={reconnecting}>
                Reconnect
              </Button>
              <Button onClick={handleSyncNow} loading={syncing}>
                Sync now
              </Button>
            </div>
          ) : (
            <Button onClick={handleReconnect} loading={reconnecting}>
              Connect Zerodha
            </Button>
          )}
        </div>

        {zerodha && portfolioValue !== null && (
          <div className="mt-4 flex flex-wrap gap-6 border-t border-rule pt-4">
            <div>
              <MetricLabel>Total portfolio value</MetricLabel>
              <div className="mt-1">
                <Money value={portfolioValue} size="md" />
              </div>
            </div>
            <div>
              <MetricLabel>Holdings</MetricLabel>
              <p className="mt-1 font-mono text-base text-ink">{holdingsCount ?? 0}</p>
            </div>
          </div>
        )}

        {reconnectStep && userId && (
          <div className="mt-4 rounded-md border border-rule bg-bg p-4 text-sm">
            <p className="font-medium text-ink">Finish connecting in the tab that just opened</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-ink-muted">
              <li>Log in and authorize on Zerodha&apos;s page.</li>
              <li>
                Zerodha will redirect to a page that fails to load — that&apos;s
                expected. Copy the full address-bar URL (it contains{" "}
                <code className="rounded bg-surface-raised px-1 py-0.5 text-xs">request_token=...</code>).
              </li>
              <li>
                Take the <code className="rounded bg-surface-raised px-1 py-0.5 text-xs">request_token</code>{" "}
                value and visit:
                <br />
                <code className="mt-1 block break-all rounded bg-surface-raised px-2 py-1 text-xs">
                  {process.env.NEXT_PUBLIC_API_URL}/brokers/zerodha/callback?user_id={userId}&request_token=PASTE_HERE
                </code>
              </li>
            </ol>
            <p className="mt-3 text-xs text-ink-faint">
              This manual step exists because Zerodha&apos;s redirect can&apos;t
              carry your FinVigil session — closing this automatically is
              tracked as a known improvement.
            </p>
            <button
              type="button"
              onClick={() => setReconnectStep(false)}
              className="mt-3 cursor-pointer text-xs font-medium text-brand hover:text-brand-hover"
            >
              Done, dismiss
            </button>
          </div>
        )}

        {syncResult && (
          <div className="mt-4 rounded-md border border-rule bg-bg p-3 text-sm text-ink-muted">
            Synced: {syncResult.imported} imported, {syncResult.skipped} skipped
            {syncResult.errors.length > 0 && `, ${syncResult.errors.length} errors`}.
          </div>
        )}
      </Card>

      {/* Angel One / Upstox — presentational only, no real backend yet */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {(["Angel One", "Upstox"] as const).map((name) => (
          <Card key={name} className="p-5">
            <div className="flex items-center justify-between">
              <p className="font-medium text-ink">{name}</p>
              <Button
                variant="secondary"
                onClick={() =>
                  setInProgressNotice(
                    `${name} integration is in progress — connecting here isn't available yet.`
                  )
                }
              >
                Connect
              </Button>
            </div>
            {inProgressNotice?.startsWith(name) && (
              <p className="mt-2 text-xs text-ink-muted">{inProgressNotice}</p>
            )}
          </Card>
        ))}
      </div>

      {/* Dhan / Kotak — coming soon, muted */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {(["Dhan", "Kotak Securities"] as const).map((name) => (
          <Card key={name} className="p-5 opacity-60">
            <div className="flex items-center justify-between">
              <p className="font-medium text-ink-muted">{name}</p>
              <Badge tone="neutral">Coming soon</Badge>
            </div>
          </Card>
        ))}
      </div>

      {/* CSV import */}
      <Card className="p-5">
        <MetricLabel>Import a tradebook</MetricLabel>
        <p className="mt-1 text-sm text-ink-muted">
          Upload a Zerodha tradebook export (.csv or .xlsx) to backfill trade
          history that isn&apos;t available via daily sync.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            aria-label="Tradebook file"
            className="text-sm text-ink-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-rule file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink hover:file:border-rule-strong"
          />
          <Button onClick={handleCsvUpload} loading={csvUploading} variant="secondary">
            Upload
          </Button>
        </div>
        {csvError && (
          <p className="mt-2 text-sm text-loss" role="alert">{csvError}</p>
        )}
        {csvResult && (
          <div className="mt-3 rounded-md border border-rule bg-bg p-3 text-sm">
            <p className="text-ink">
              {csvResult.imported} imported, {csvResult.skipped} skipped, of{" "}
              {csvResult.total_rows} rows.
            </p>
            {csvResult.errors.length > 0 && (
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-loss">
                {csvResult.errors.slice(0, 5).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

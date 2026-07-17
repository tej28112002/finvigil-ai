"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
  api_key: string | null;
  has_credentials: boolean;
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

const ZERODHA_CALLBACK_URL = `${process.env.NEXT_PUBLIC_API_URL}/brokers/zerodha/callback`;

export default function BrokersPage() {
  return (
    <Suspense fallback={null}>
      <BrokersPageInner />
    </Suspense>
  );
}

function BrokersPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [brokers, setBrokers] = useState<BrokerConnection[] | null>(null);
  const [portfolioValue, setPortfolioValue] = useState<string | null>(null);
  const [holdingsCount, setHoldingsCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Set by the backend redirecting back here after /brokers/zerodha/callback
  // completes (or fails) — see app/api/v1/zerodha.py.
  const [callbackNotice, setCallbackNotice] = useState<
    { tone: "success" | "error"; message: string } | null
  >(null);

  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<CsvImportResult | null>(null);
  const [lastSynced, setLastSynced] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  // BYOK credential form
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [submittingCredentials, setSubmittingCredentials] = useState(false);
  const [credentialsError, setCredentialsError] = useState<string | null>(null);

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
      await supabase.auth.getSession();

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

  // Read ?zerodha=connected|error&message=... left by the backend redirect,
  // show a one-time banner, then strip it so a refresh doesn't re-show it.
  useEffect(() => {
    const zerodhaResult = searchParams.get("zerodha");
    if (zerodhaResult === "connected") {
      setCallbackNotice({ tone: "success", message: "Zerodha connected." });
      writeLastSynced();
      setLastSynced(readLastSynced());
      router.replace("/brokers");
      load();
    } else if (zerodhaResult === "error") {
      setCallbackNotice({
        tone: "error",
        message: searchParams.get("message") || "Could not connect Zerodha.",
      });
      router.replace("/brokers");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const zerodha = brokers?.find((b) => b.broker_name === "zerodha") ?? null;
  const csvConn = brokers?.find((b) => b.broker_name === "csv") ?? null;

  async function handleSubmitCredentials(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingCredentials(true);
    setCredentialsError(null);
    try {
      const updated = await apiFetch<BrokerConnection>(
        "/brokers/zerodha/credentials",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret }),
        }
      );
      setBrokers((prev) => {
        if (!prev) return [updated];
        const withoutZerodha = prev.filter((b) => b.broker_name !== "zerodha");
        return [...withoutZerodha, updated];
      });
      setApiKey("");
      setApiSecret("");
    } catch (err) {
      setCredentialsError(
        err instanceof Error ? err.message : "Could not save credentials"
      );
    } finally {
      setSubmittingCredentials(false);
    }
  }

  async function handleConnect() {
    setConnecting(true);
    setError(null);
    try {
      const { login_url } = await apiFetch<{ login_url: string }>(
        "/brokers/zerodha/login"
      );
      // Full-page navigation, same tab: Zerodha's redirect now carries a
      // signed state token, so the backend callback can complete the login
      // and redirect straight back to /brokers on its own — no more manual
      // "open in a new tab, copy the request_token, paste it here" step.
      window.location.href = login_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start connect");
      setConnecting(false);
    }
  }

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
      {callbackNotice && (
        <Card className="p-4">
          <p
            className={`text-sm ${callbackNotice.tone === "error" ? "text-loss" : "text-ink"}`}
            role={callbackNotice.tone === "error" ? "alert" : "status"}
          >
            {callbackNotice.message}
          </p>
        </Card>
      )}

      {error && (
        <Card className="p-4">
          <p className="text-sm text-loss" role="alert">{error}</p>
        </Card>
      )}

      {/* Zerodha — bring-your-own-key */}
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
            <span
              className="h-3 w-3 shrink-0 rounded-sm"
              style={{ backgroundColor: "var(--color-broker-zerodha)" }}
              aria-hidden="true"
            />
            <div>
              <p className="font-medium text-ink">Zerodha</p>
              <p className="text-xs text-ink-muted">
                {zerodha?.status === "active"
                  ? "Connected"
                  : zerodha?.has_credentials
                    ? "Credentials saved — not yet connected"
                    : "Not set up"}
                {lastSynced && zerodha?.status === "active" && (
                  <> · Last synced {new Date(lastSynced).toLocaleString("en-IN")}</>
                )}
              </p>
            </div>
          </div>

          {zerodha?.status === "active" && (
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleConnect} loading={connecting}>
                Reconnect
              </Button>
              <Button onClick={handleSyncNow} loading={syncing}>
                Sync now
              </Button>
            </div>
          )}
          {zerodha?.has_credentials && zerodha.status !== "active" && (
            <Button onClick={handleConnect} loading={connecting}>
              Connect Zerodha
            </Button>
          )}
        </div>

        {zerodha?.status === "active" && portfolioValue !== null && (
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

        {!zerodha?.has_credentials && (
          <div className="mt-4 rounded-md border border-rule bg-bg p-4 text-sm">
            <p className="font-medium text-ink">Set up your own Kite Connect app</p>
            <p className="mt-1 text-ink-muted">
              FinVigil no longer uses a shared broker key — you connect using
              your own Zerodha developer app, the same way you would with
              AlgoTest or Sensibull. Your API key and secret are encrypted
              and never shared with other users.
            </p>
            <ol className="mt-3 list-decimal space-y-2 pl-4 text-ink-muted">
              <li>
                Go to{" "}
                <a
                  href="https://developers.kite.trade/apps"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-brand hover:text-brand-hover"
                >
                  developers.kite.trade/apps
                </a>{" "}
                and create a new Connect app. This requires a Kite Connect
                subscription (₹500/month, billed by Zerodha directly).
              </li>
              <li>
                Set the app&apos;s <strong>Redirect URL</strong> to exactly:
                <code className="mt-1 block break-all rounded bg-surface-raised px-2 py-1 text-xs">
                  {ZERODHA_CALLBACK_URL}
                </code>
              </li>
              <li>Copy the app&apos;s API key and API secret and paste them below.</li>
            </ol>

            <form onSubmit={handleSubmitCredentials} className="mt-4 space-y-3">
              <div>
                <label htmlFor="zerodha-api-key" className="mb-1 block text-xs font-medium text-ink">
                  API key
                </label>
                <input
                  id="zerodha-api-key"
                  type="text"
                  required
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                  placeholder="e.g. 6uamrld2mc32anjc"
                />
              </div>
              <div>
                <label htmlFor="zerodha-api-secret" className="mb-1 block text-xs font-medium text-ink">
                  API secret
                </label>
                <input
                  id="zerodha-api-secret"
                  type="password"
                  required
                  autoComplete="off"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                  placeholder="Kept encrypted, never shown again"
                />
              </div>
              {credentialsError && (
                <p className="text-sm text-loss" role="alert">{credentialsError}</p>
              )}
              <Button type="submit" loading={submittingCredentials}>
                Save credentials
              </Button>
            </form>
          </div>
        )}

        {syncResult && (
          <div className="mt-4 rounded-md border border-rule bg-bg p-3 text-sm text-ink-muted">
            Synced: {syncResult.imported} imported, {syncResult.skipped} skipped
            {syncResult.errors.length > 0 && `, ${syncResult.errors.length} errors`}.
          </div>
        )}
      </Card>

      {/* Upstox / Groww — presentational only, no real backend yet */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {(["Upstox", "Groww"] as const).map((name) => (
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

      {/* Angel One / Dhan / Kotak — coming soon, muted */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {(["Angel One", "Dhan", "Kotak Securities"] as const).map((name) => (
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

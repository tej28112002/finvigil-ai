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

function lastSyncedKey(brokerName: string): string {
  return `finvigil-last-synced-${brokerName}`;
}

function readLastSynced(brokerName: string): string | null {
  try {
    return window.localStorage.getItem(lastSyncedKey(brokerName));
  } catch {
    return null;
  }
}

function writeLastSynced(brokerName: string) {
  try {
    window.localStorage.setItem(lastSyncedKey(brokerName), new Date().toISOString());
  } catch {
    // non-fatal — just a display nicety
  }
}

const ZERODHA_CALLBACK_URL = `${process.env.NEXT_PUBLIC_API_URL}/brokers/zerodha/callback`;
const UPSTOX_CALLBACK_URL = `${process.env.NEXT_PUBLIC_API_URL}/brokers/upstox/callback`;

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

  const [callbackNotice, setCallbackNotice] = useState<
    { tone: "success" | "error"; message: string } | null
  >(null);

  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<CsvImportResult | null>(null);
  const [zerodhaLastSynced, setZerodhaLastSynced] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  // BYOK credential form (Zerodha)
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [submittingCredentials, setSubmittingCredentials] = useState(false);
  const [credentialsError, setCredentialsError] = useState<string | null>(null);

  // Upstox
  const [upstoxSyncing, setUpstoxSyncing] = useState(false);
  const [upstoxSyncResult, setUpstoxSyncResult] = useState<CsvImportResult | null>(null);
  const [upstoxLastSynced, setUpstoxLastSynced] = useState<string | null>(null);
  const [upstoxConnecting, setUpstoxConnecting] = useState(false);
  const [upstoxApiKey, setUpstoxApiKey] = useState("");
  const [upstoxApiSecret, setUpstoxApiSecret] = useState("");
  const [submittingUpstoxCredentials, setSubmittingUpstoxCredentials] = useState(false);
  const [upstoxCredentialsError, setUpstoxCredentialsError] = useState<string | null>(null);

  // Groww — TOTP-based
  const [growwSyncing, setGrowwSyncing] = useState(false);
  const [growwSyncResult, setGrowwSyncResult] = useState<CsvImportResult | null>(null);
  const [growwLastSynced, setGrowwLastSynced] = useState<string | null>(null);
  const [growwApiKey, setGrowwApiKey] = useState("");
  const [growwTotpSecret, setGrowwTotpSecret] = useState("");
  const [submittingGrowwCredentials, setSubmittingGrowwCredentials] = useState(false);
  const [growwCredentialsError, setGrowwCredentialsError] = useState<string | null>(null);

  const [csvUploading, setCsvUploading] = useState(false);
  const [csvResult, setCsvResult] = useState<CsvImportResult | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Accordion + search state
  const [expandedBroker, setExpandedBroker] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  function toggleBroker(key: string) {
    setExpandedBroker((prev) => (prev === key ? null : key));
  }

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
      setZerodhaLastSynced(readLastSynced("zerodha"));
      setUpstoxLastSynced(readLastSynced("upstox"));
      setGrowwLastSynced(readLastSynced("groww"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load brokers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const zerodhaResult = searchParams.get("zerodha");
    if (zerodhaResult === "connected") {
      setCallbackNotice({ tone: "success", message: "Zerodha connected." });
      setExpandedBroker("zerodha");
      writeLastSynced("zerodha");
      setZerodhaLastSynced(readLastSynced("zerodha"));
      router.replace("/brokers");
      load();
    } else if (zerodhaResult === "error") {
      setCallbackNotice({
        tone: "error",
        message: searchParams.get("message") || "Could not connect Zerodha.",
      });
      setExpandedBroker("zerodha");
      router.replace("/brokers");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    const upstoxResult = searchParams.get("upstox");
    if (upstoxResult === "connected") {
      setCallbackNotice({ tone: "success", message: "Upstox connected." });
      setExpandedBroker("upstox");
      writeLastSynced("upstox");
      setUpstoxLastSynced(readLastSynced("upstox"));
      router.replace("/brokers");
      load();
    } else if (upstoxResult === "error") {
      setCallbackNotice({
        tone: "error",
        message: searchParams.get("message") || "Could not connect Upstox.",
      });
      setExpandedBroker("upstox");
      router.replace("/brokers");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const zerodha = brokers?.find((b) => b.broker_name === "zerodha") ?? null;
  const upstox = brokers?.find((b) => b.broker_name === "upstox") ?? null;
  const groww = brokers?.find((b) => b.broker_name === "groww") ?? null;
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
      writeLastSynced("zerodha");
      setZerodhaLastSynced(readLastSynced("zerodha"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function handleSubmitUpstoxCredentials(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingUpstoxCredentials(true);
    setUpstoxCredentialsError(null);
    try {
      const updated = await apiFetch<BrokerConnection>(
        "/brokers/upstox/credentials",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: upstoxApiKey, api_secret: upstoxApiSecret }),
        }
      );
      setBrokers((prev) => {
        if (!prev) return [updated];
        const withoutUpstox = prev.filter((b) => b.broker_name !== "upstox");
        return [...withoutUpstox, updated];
      });
      setUpstoxApiKey("");
      setUpstoxApiSecret("");
    } catch (err) {
      setUpstoxCredentialsError(
        err instanceof Error ? err.message : "Could not save credentials"
      );
    } finally {
      setSubmittingUpstoxCredentials(false);
    }
  }

  async function handleConnectUpstox() {
    setUpstoxConnecting(true);
    setError(null);
    try {
      const { login_url } = await apiFetch<{ login_url: string }>(
        "/brokers/upstox/login"
      );
      window.location.href = login_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start connect");
      setUpstoxConnecting(false);
    }
  }

  async function handleSyncUpstoxNow() {
    if (!upstox) return;
    setUpstoxSyncing(true);
    setUpstoxSyncResult(null);
    setError(null);
    try {
      const result = await apiFetch<CsvImportResult>(
        `/brokers/upstox/sync?broker_connection_id=${upstox.id}`,
        { method: "POST" }
      );
      setUpstoxSyncResult(result);
      writeLastSynced("upstox");
      setUpstoxLastSynced(readLastSynced("upstox"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setUpstoxSyncing(false);
    }
  }

  async function handleSubmitGrowwCredentials(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingGrowwCredentials(true);
    setGrowwCredentialsError(null);
    try {
      const updated = await apiFetch<BrokerConnection>(
        "/brokers/groww/credentials",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: growwApiKey, totp_secret: growwTotpSecret }),
        }
      );
      setBrokers((prev) => {
        if (!prev) return [updated];
        const withoutGroww = prev.filter((b) => b.broker_name !== "groww");
        return [...withoutGroww, updated];
      });
      setGrowwApiKey("");
      setGrowwTotpSecret("");
    } catch (err) {
      setGrowwCredentialsError(
        err instanceof Error ? err.message : "Could not save credentials"
      );
    } finally {
      setSubmittingGrowwCredentials(false);
    }
  }

  async function handleSyncGrowwNow() {
    if (!groww) return;
    setGrowwSyncing(true);
    setGrowwSyncResult(null);
    setError(null);
    try {
      const result = await apiFetch<CsvImportResult>(
        `/brokers/groww/sync?broker_connection_id=${groww.id}`,
        { method: "POST" }
      );
      setGrowwSyncResult(result);
      writeLastSynced("groww");
      setGrowwLastSynced(readLastSynced("groww"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setGrowwSyncing(false);
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

  // Search filter helper
  const q = searchQuery.toLowerCase().trim();
  const visible = (name: string) => !q || name.toLowerCase().includes(q);

  const COMING_SOON = ["Angel One", "Dhan", "Kotak Securities"] as const;

  return (
    <div className="mx-auto max-w-5xl space-y-4">
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

      {/* Search */}
      <div>
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search your broker…"
          aria-label="Search brokers"
          className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand focus:outline-none"
        />
      </div>

      {/* ── Zerodha ───────────────────────────────────────────────────── */}
      {visible("Zerodha") && (
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
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
                  {zerodhaLastSynced && zerodha?.status === "active" && (
                    <> · Last synced {new Date(zerodhaLastSynced).toLocaleString("en-IN")}</>
                  )}
                </p>
              </div>
            </div>

            <Button
              variant={zerodha?.status === "active" ? "secondary" : "primary"}
              onClick={() => toggleBroker("zerodha")}
              aria-expanded={expandedBroker === "zerodha"}
            >
              {zerodha?.status === "active" ? "Manage" : "Connect"}
            </Button>
          </div>

          {expandedBroker === "zerodha" && (
            <div className="mt-4 space-y-4 border-t border-rule pt-4">
              {/* Active: portfolio summary + sync/reconnect */}
              {zerodha?.status === "active" && (
                <>
                  {portfolioValue !== null && (
                    <div className="flex flex-wrap gap-6">
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
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={handleConnect} loading={connecting}>
                      Reconnect
                    </Button>
                    <Button onClick={handleSyncNow} loading={syncing}>
                      Sync now
                    </Button>
                  </div>
                  {syncResult && (
                    <div className="rounded-md border border-rule bg-bg p-3 text-sm text-ink-muted">
                      Synced: {syncResult.imported} imported, {syncResult.skipped} skipped
                      {syncResult.errors.length > 0 && `, ${syncResult.errors.length} errors`}.
                    </div>
                  )}
                </>
              )}

              {/* Has credentials but not connected: show OAuth button */}
              {zerodha?.has_credentials && zerodha.status !== "active" && (
                <Button onClick={handleConnect} loading={connecting}>
                  Connect Zerodha
                </Button>
              )}

              {/* No credentials: setup instructions + form */}
              {!zerodha?.has_credentials && (
                <div className="rounded-md border border-rule bg-bg p-4 text-sm">
                  <p className="font-medium text-ink">Set up your own Kite Connect app</p>
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
                      and create a new Connect app.
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
            </div>
          )}
        </Card>
      )}

      {/* ── Upstox ────────────────────────────────────────────────────── */}
      {visible("Upstox") && (
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor: upstox?.status === "active" ? "var(--gain)" : "var(--ink-faint)",
                }}
                aria-hidden="true"
              />
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: "var(--color-broker-upstox)" }}
                aria-hidden="true"
              />
              <div>
                <p className="font-medium text-ink">Upstox</p>
                <p className="text-xs text-ink-muted">
                  {upstox?.status === "active"
                    ? "Connected"
                    : upstox?.has_credentials
                      ? "Credentials saved — not yet connected"
                      : "Not set up"}
                  {upstoxLastSynced && upstox?.status === "active" && (
                    <> · Last synced {new Date(upstoxLastSynced).toLocaleString("en-IN")}</>
                  )}
                </p>
              </div>
            </div>

            <Button
              variant={upstox?.status === "active" ? "secondary" : "primary"}
              onClick={() => toggleBroker("upstox")}
              aria-expanded={expandedBroker === "upstox"}
            >
              {upstox?.status === "active" ? "Manage" : "Connect"}
            </Button>
          </div>

          {expandedBroker === "upstox" && (
            <div className="mt-4 space-y-4 border-t border-rule pt-4">
              {/* Active: sync/reconnect */}
              {upstox?.status === "active" && (
                <>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={handleConnectUpstox} loading={upstoxConnecting}>
                      Reconnect
                    </Button>
                    <Button onClick={handleSyncUpstoxNow} loading={upstoxSyncing}>
                      Sync now
                    </Button>
                  </div>
                  {upstoxSyncResult && (
                    <div className="rounded-md border border-rule bg-bg p-3 text-sm text-ink-muted">
                      Synced: {upstoxSyncResult.imported} imported, {upstoxSyncResult.skipped} skipped
                      {upstoxSyncResult.errors.length > 0 && `, ${upstoxSyncResult.errors.length} errors`}.
                    </div>
                  )}
                </>
              )}

              {/* Has credentials but not connected: OAuth button */}
              {upstox?.has_credentials && upstox.status !== "active" && (
                <Button onClick={handleConnectUpstox} loading={upstoxConnecting}>
                  Connect Upstox
                </Button>
              )}

              {/* No credentials: setup instructions + form */}
              {!upstox?.has_credentials && (
                <div className="rounded-md border border-rule bg-bg p-4 text-sm">
                  <p className="font-medium text-ink">Set up your own Upstox app</p>
                  <ol className="mt-3 list-decimal space-y-2 pl-4 text-ink-muted">
                    <li>
                      Go to{" "}
                      <a
                        href="https://account.upstox.com/developer/apps"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-brand hover:text-brand-hover"
                      >
                        account.upstox.com/developer/apps
                      </a>{" "}
                      and create a new app.
                    </li>
                    <li>
                      Set the app&apos;s <strong>Redirect URI</strong> to exactly:
                      <code className="mt-1 block break-all rounded bg-surface-raised px-2 py-1 text-xs">
                        {UPSTOX_CALLBACK_URL}
                      </code>
                    </li>
                    <li>Copy the app&apos;s API key and API secret and paste them below.</li>
                  </ol>

                  <form onSubmit={handleSubmitUpstoxCredentials} className="mt-4 space-y-3">
                    <div>
                      <label htmlFor="upstox-api-key" className="mb-1 block text-xs font-medium text-ink">
                        API key
                      </label>
                      <input
                        id="upstox-api-key"
                        type="text"
                        required
                        value={upstoxApiKey}
                        onChange={(e) => setUpstoxApiKey(e.target.value)}
                        className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                        placeholder="Client ID"
                      />
                    </div>
                    <div>
                      <label htmlFor="upstox-api-secret" className="mb-1 block text-xs font-medium text-ink">
                        API secret
                      </label>
                      <input
                        id="upstox-api-secret"
                        type="password"
                        required
                        autoComplete="off"
                        value={upstoxApiSecret}
                        onChange={(e) => setUpstoxApiSecret(e.target.value)}
                        className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                        placeholder="Kept encrypted, never shown again"
                      />
                    </div>
                    {upstoxCredentialsError && (
                      <p className="text-sm text-loss" role="alert">{upstoxCredentialsError}</p>
                    )}
                    <Button type="submit" loading={submittingUpstoxCredentials}>
                      Save credentials
                    </Button>
                  </form>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── Groww ─────────────────────────────────────────────────────── */}
      {visible("Groww") && (
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor: groww?.status === "active" ? "var(--gain)" : "var(--ink-faint)",
                }}
                aria-hidden="true"
              />
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: "var(--color-broker-groww, #00d09c)" }}
                aria-hidden="true"
              />
              <div>
                <p className="font-medium text-ink">Groww</p>
                <p className="text-xs text-ink-muted">
                  {groww?.status === "active"
                    ? "Connected"
                    : groww?.has_credentials
                      ? "Credentials saved — sync to verify"
                      : "Not set up"}
                  {growwLastSynced && groww?.status === "active" && (
                    <> · Last synced {new Date(growwLastSynced).toLocaleString("en-IN")}</>
                  )}
                </p>
              </div>
            </div>

            <Button
              variant={groww?.has_credentials ? "secondary" : "primary"}
              onClick={() => toggleBroker("groww")}
              aria-expanded={expandedBroker === "groww"}
            >
              {groww?.has_credentials ? "Manage" : "Connect"}
            </Button>
          </div>

          {expandedBroker === "groww" && (
            <div className="mt-4 space-y-4 border-t border-rule pt-4">
              {/* Has credentials: sync + update form */}
              {groww?.has_credentials && (
                <>
                  <Button onClick={handleSyncGrowwNow} loading={growwSyncing}>
                    Sync now
                  </Button>
                  {growwSyncResult && (
                    <div className="rounded-md border border-rule bg-bg p-3 text-sm text-ink-muted">
                      Synced: {growwSyncResult.imported} imported, {growwSyncResult.skipped} skipped
                      {growwSyncResult.errors.length > 0 && `, ${growwSyncResult.errors.length} errors`}.
                    </div>
                  )}
                  <p className="text-xs text-ink-muted">Update credentials:</p>
                </>
              )}

              {/* Setup or update form */}
              <div className={groww?.has_credentials ? "" : "rounded-md border border-rule bg-bg p-4 text-sm"}>
                {!groww?.has_credentials && (
                  <>
                    <p className="font-medium text-ink">Set up your own Groww Trade API key</p>
                    <ol className="mt-3 list-decimal space-y-2 pl-4 text-ink-muted">
                      <li>
                        Go to{" "}
                        <a
                          href="https://groww.in/trade-api"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-brand hover:text-brand-hover"
                        >
                          groww.in/trade-api
                        </a>{" "}
                        and subscribe to the API plan.
                      </li>
                      <li>
                        From your Groww account, open Trade API settings and generate your API key.
                      </li>
                      <li>
                        Make sure TOTP is enabled on your account (Settings → Security), then copy
                        your TOTP secret from the Groww Trade API console.
                      </li>
                      <li>Paste both values below — no redirect URL is needed.</li>
                    </ol>
                  </>
                )}

                <form onSubmit={handleSubmitGrowwCredentials} className={`space-y-3 ${!groww?.has_credentials ? "mt-4" : ""}`}>
                  <div>
                    <label htmlFor="groww-api-key" className="mb-1 block text-xs font-medium text-ink">
                      API key
                    </label>
                    <input
                      id="groww-api-key"
                      type="text"
                      required
                      value={growwApiKey}
                      onChange={(e) => setGrowwApiKey(e.target.value)}
                      className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                      placeholder="Your Groww API key"
                    />
                  </div>
                  <div>
                    <label htmlFor="groww-totp-secret" className="mb-1 block text-xs font-medium text-ink">
                      TOTP secret
                    </label>
                    <input
                      id="groww-totp-secret"
                      type="password"
                      required
                      autoComplete="off"
                      value={growwTotpSecret}
                      onChange={(e) => setGrowwTotpSecret(e.target.value)}
                      className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-brand"
                      placeholder="Kept encrypted, never shown again"
                    />
                  </div>
                  {growwCredentialsError && (
                    <p className="text-sm text-loss" role="alert">{growwCredentialsError}</p>
                  )}
                  <Button type="submit" loading={submittingGrowwCredentials}>
                    {groww?.has_credentials ? "Update credentials" : "Save credentials"}
                  </Button>
                </form>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* ── Coming soon ───────────────────────────────────────────────── */}
      {COMING_SOON.some((name) => visible(name)) && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {COMING_SOON.filter((name) => visible(name)).map((name) => (
            <Card key={name} className="p-5 opacity-60">
              <div className="flex items-center justify-between">
                <p className="font-medium text-ink-muted">{name}</p>
                <Badge tone="neutral">Coming soon</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ── CSV import ────────────────────────────────────────────────── */}
      {visible("CSV Import") && (
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
      )}
    </div>
  );
}

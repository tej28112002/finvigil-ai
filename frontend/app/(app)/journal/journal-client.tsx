"use client";

import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { BrokerActionsBar } from "@/components/shared/broker-actions-bar";
import { apiFetch, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

// ── types ────────────────────────────────────────────────────────────────────

interface JournalTag {
  id: string;
  tag_name: string;
}

interface JournalEntry {
  id: string;
  transcript: string;
  created_at: string;
}

interface JournalEntryWithTags {
  entry: JournalEntry;
  tags: JournalTag[];
}

interface Profitability {
  net_profit: number | null;
  avg_daily_pnl: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  avg_trade_return: number | null;
  total_return_pct: number | null;
}
interface WinLoss {
  win_rate_pct: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  payoff_ratio: number | null;
  largest_win: number | null;
  largest_loss: number | null;
  total_trades: number;
  win_count: number;
  loss_count: number;
}
interface RiskMetrics {
  max_drawdown_pct: number | null;
  daily_pnl_volatility: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  risk_per_trade_pct: number | null;
  daily_loss_limit_pct: number | null;
}
interface Efficiency {
  total_trades: number;
  trades_per_day_avg: number | null;
  avg_holding_days: number | null;
  total_trading_days: number;
  profitable_days: number;
  pct_profitable_days: number | null;
  recovery_factor: number | null;
}
interface CostExecution {
  total_charges: number | null;
  avg_charge_per_trade: number | null;
  breakeven_win_rate_pct: number | null;
  slippage_avg: number | null;
  turnover_ratio: number | null;
  note: string;
}
interface EquityPoint {
  date: string;
  cumulative_pnl: number;
  daily_pnl: number;
}
interface AnalyticsResponse {
  profitability: Profitability | null;
  win_loss: WinLoss | null;
  risk: RiskMetrics | null;
  efficiency: Efficiency | null;
  cost_execution: CostExecution | null;
  equity_curve: EquityPoint[] | null;
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

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

function rupeeStr(v: number | null): string {
  if (v === null) return "—";
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  return `${sign}₹${abs.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function pctStr(v: number | null): string {
  if (v === null) return "—";
  return `${v.toFixed(2)}%`;
}

function ratioStr(v: number | null): string {
  if (v === null) return "—";
  return v.toFixed(2);
}

// tone: green if > 0, red if < 0, neutral otherwise
function colorSign(v: number | null): string {
  if (v === null) return "text-ink-faint";
  if (v > 0) return "text-gain";
  if (v < 0) return "text-loss";
  return "text-ink";
}

// tone: green if > 0, red if <= 0 (used for expectancy)
function colorPositiveElseLoss(v: number | null): string {
  if (v === null) return "text-ink-faint";
  return v > 0 ? "text-gain" : "text-loss";
}

// green >= good, yellow (estimate) in the middle band, red below
function colorBand(v: number | null, good: number, mid: number): string {
  if (v === null) return "text-ink-faint";
  if (v >= good) return "text-gain";
  if (v >= mid) return "text-estimate";
  return "text-loss";
}

// green >= good, yellow in the middle band, otherwise neutral (no red rule given)
function colorBandNoRed(v: number | null, good: number, mid: number): string {
  if (v === null) return "text-ink-faint";
  if (v >= good) return "text-gain";
  if (v >= mid) return "text-estimate";
  return "text-ink";
}

// apiFetch always parses JSON; audio upload needs FormData + a raw
// multipart POST, so this bypasses apiFetch the same way ca-bundle-button
// does for its binary download.
async function uploadAudio(blob: Blob): Promise<JournalEntryWithTags> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    window.location.href = "/login";
    throw new Error("No active session");
  }

  const formData = new FormData();
  formData.append("file", blob, "recording.webm");

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/journal/entries/audio`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: formData,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

// ── small shared UI ──────────────────────────────────────────────────────────

function MetricSkeleton() {
  return <div className="h-8 w-24 animate-pulse rounded bg-rule" />;
}

function InfoTip({ text }: { text: string }) {
  return (
    <span title={text} className="cursor-help text-ink-faint" aria-label="Info">
      {" "}ⓘ
    </span>
  );
}

function MetricCard({
  label,
  value,
  colorClass = "text-ink",
  subtitle,
  tooltip,
  loading,
}: {
  label: string;
  value: string | null;
  colorClass?: string;
  subtitle?: string;
  tooltip?: string;
  loading: boolean;
}) {
  return (
    <Card className="p-5">
      <MetricLabel>
        {label}
        {tooltip && <InfoTip text={tooltip} />}
      </MetricLabel>
      <div className="mt-3">
        {loading ? (
          <MetricSkeleton />
        ) : value !== null ? (
          <span className={`font-mono text-2xl font-medium ${colorClass}`}>{value}</span>
        ) : (
          <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-ink-faint">{loading ? "Loading…" : subtitle}</p>}
    </Card>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="mt-8 font-display text-lg text-ink">{children}</h2>;
}

// ── equity curve chart (hand-rolled SVG, no chart library) ────────────────────

function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (data.length < 3) {
    return (
      <p className="text-sm text-ink-faint">
        Not enough trade history to draw equity curve.
      </p>
    );
  }

  const width = 800;
  const height = 200;
  const padding = 28;

  const values = data.map((d) => d.cumulative_pnl);
  const minVal = Math.min(...values, 0);
  const maxVal = Math.max(...values, 0);
  const range = maxVal - minVal || 1;

  const xStep = data.length > 1 ? (width - padding * 2) / (data.length - 1) : 0;
  const points = data.map((d, i) => ({
    x: padding + i * xStep,
    y: padding + (1 - (d.cumulative_pnl - minVal) / range) * (height - padding * 2),
    ...d,
  }));

  const zeroY = padding + (1 - (0 - minVal) / range) * (height - padding * 2);
  const isPositive = values[values.length - 1] >= 0;
  const lineColor = isPositive ? "var(--color-gain)" : "var(--color-loss)";
  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(" ");

  function handleMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * width;
    let nearest = 0;
    let minDist = Infinity;
    points.forEach((p, i) => {
      const dist = Math.abs(p.x - relX);
      if (dist < minDist) {
        minDist = dist;
        nearest = i;
      }
    });
    setHoverIdx(nearest);
  }

  const hovered = hoverIdx !== null ? points[hoverIdx] : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverIdx(null)}
        className="overflow-visible"
      >
        <line
          x1={padding}
          y1={zeroY}
          x2={width - padding}
          y2={zeroY}
          stroke="var(--color-rule)"
          strokeDasharray="4 4"
        />
        <polyline points={polylinePoints} fill="none" stroke={lineColor} strokeWidth="2" />
        {hovered && (
          <>
            <line
              x1={hovered.x}
              y1={padding}
              x2={hovered.x}
              y2={height - padding}
              stroke="var(--color-rule)"
              strokeWidth="1"
            />
            <circle cx={hovered.x} cy={hovered.y} r="4" fill={lineColor} />
          </>
        )}
      </svg>
      {hovered && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border border-rule bg-surface px-2 py-1 text-xs shadow-token-sm"
          style={{ left: `${(hovered.x / width) * 100}%`, top: 0 }}
        >
          <div className="text-ink-muted">{hovered.date}</div>
          <div className={`font-mono ${colorSign(hovered.cumulative_pnl)}`}>
            {rupeeStr(hovered.cumulative_pnl)}
          </div>
        </div>
      )}
      <div className="mt-2 flex justify-between text-xs text-ink-faint">
        <span>
          {data[0].date} · {rupeeStr(data[0].cumulative_pnl)}
        </span>
        <span>
          {data[data.length - 1].date} · {rupeeStr(data[data.length - 1].cumulative_pnl)}
        </span>
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function JournalClient() {
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [entries, setEntries] = useState<JournalEntryWithTags[] | null>(null);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [micUnsupported, setMicUnsupported] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [textInput, setTextInput] = useState("");
  const [submittingText, setSubmittingText] = useState(false);

  const [pendingEntry, setPendingEntry] = useState<JournalEntryWithTags | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [savingTags, setSavingTags] = useState(false);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  async function loadEntries() {
    setLoadingEntries(true);
    try {
      const data = await apiFetch<JournalEntryWithTags[]>("/journal/entries");
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load journal entries.");
    } finally {
      setLoadingEntries(false);
    }
  }

  function loadAnalytics() {
    setAnalyticsLoading(true);
    apiFetch<AnalyticsResponse>("/journal/analytics")
      .then((data) => setAnalytics(data))
      .catch(() => setAnalytics(null))
      .finally(() => setAnalyticsLoading(false));
  }

  useEffect(() => {
    apiFetch<{ tags: Record<string, string> }>("/journal/tags/taxonomy")
      .then((r) => setTaxonomy(r.tags))
      .catch(() => setTaxonomy({}));
    loadEntries();
    loadAnalytics();
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setMicUnsupported(true);
    }
  }, []);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setTranscribing(true);
        try {
          const result = await uploadAudio(blob);
          setPendingEntry(result);
          setSelectedTags([]);
          await loadEntries();
        } catch (err) {
          if (err instanceof ApiError && err.status === 503) {
            setError(
              "Voice transcription isn't configured yet on the server — try typing your entry below instead."
            );
          } else {
            setError(err instanceof Error ? err.message : "Transcription failed.");
          }
        } finally {
          setTranscribing(false);
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Microphone access was denied or unavailable.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  async function handleTextSubmit() {
    if (!textInput.trim()) {
      setError("Write something before submitting.");
      return;
    }
    setError(null);
    setSubmittingText(true);
    try {
      const result = await apiFetch<JournalEntryWithTags>("/journal/entries/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: textInput }),
      });
      setPendingEntry(result);
      setSelectedTags([]);
      setTextInput("");
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save entry.");
    } finally {
      setSubmittingText(false);
    }
  }

  function toggleTag(tag: string) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function handleSaveTags() {
    if (!pendingEntry || selectedTags.length === 0) {
      setPendingEntry(null);
      return;
    }
    setSavingTags(true);
    try {
      await apiFetch(`/journal/entries/${pendingEntry.entry.id}/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag_names: selectedTags }),
      });
      setPendingEntry(null);
      setSelectedTags([]);
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save tags.");
    } finally {
      setSavingTags(false);
    }
  }

  async function handleDelete(entryId: string) {
    setDeletingId(entryId);
    try {
      await apiFetch(`/journal/entries/${entryId}`, { method: "DELETE" });
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete entry.");
    } finally {
      setDeletingId(null);
    }
  }

  const p = analytics?.profitability ?? null;
  const wl = analytics?.win_loss ?? null;
  const risk = analytics?.risk ?? null;
  const eff = analytics?.efficiency ?? null;
  const equityCurve = analytics?.equity_curve ?? null;

  const hasNoData =
    !analyticsLoading && analytics !== null && !p && !wl && !risk && !eff && !equityCurve;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">AI Journaling</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your trading performance, automatically computed from your trade history.
        </p>
      </div>

      <BrokerActionsBar
        onUploadSuccess={() => {
          loadAnalytics();
          loadEntries();
        }}
      />

      {hasNoData ? (
        <EmptyState
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 3v18h18" />
              <path d="M7 15l4-6 3 3 5-8" />
            </svg>
          }
          title="No trade history found"
          description="Sync your broker or import a tradebook to see your trading analytics."
          action={
            <Button onClick={() => (window.location.href = "/brokers")}>
              Go to Brokers →
            </Button>
          }
        />
      ) : (
        <>
          {/* SECTION 1 — Profitability */}
          <SectionLabel>Profitability</SectionLabel>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <MetricCard
              label="Net Profit"
              value={analyticsLoading ? null : rupeeStr(p?.net_profit ?? null)}
              colorClass={colorSign(p?.net_profit ?? null)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Avg Daily P&L"
              value={analyticsLoading ? null : rupeeStr(p?.avg_daily_pnl ?? null)}
              colorClass={colorSign(p?.avg_daily_pnl ?? null)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Profit Factor"
              value={analyticsLoading ? null : ratioStr(p?.profit_factor ?? null)}
              colorClass={colorBand(p?.profit_factor ?? null, 1.5, 1.0)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Expectancy"
              value={analyticsLoading ? null : rupeeStr(p?.expectancy ?? null)}
              colorClass={colorPositiveElseLoss(p?.expectancy ?? null)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Avg Trade Return"
              value={analyticsLoading ? null : rupeeStr(p?.avg_trade_return ?? null)}
              colorClass={colorSign(p?.avg_trade_return ?? null)}
              loading={analyticsLoading}
            />
          </div>

          {/* SECTION 2 — Win / Loss */}
          <SectionLabel>Win / Loss</SectionLabel>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="Win Rate"
              value={analyticsLoading ? null : pctStr(wl?.win_rate_pct ?? null)}
              colorClass={colorBand(wl?.win_rate_pct ?? null, 55, 45)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Total Trades"
              value={analyticsLoading ? null : wl ? String(wl.total_trades) : null}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Win Count vs Loss Count"
              value={analyticsLoading ? null : wl ? `${wl.win_count} / ${wl.loss_count}` : null}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Avg Win"
              value={analyticsLoading ? null : rupeeStr(wl?.avg_win ?? null)}
              colorClass="text-gain"
              loading={analyticsLoading}
            />
            <MetricCard
              label="Avg Loss"
              value={analyticsLoading ? null : rupeeStr(wl?.avg_loss ?? null)}
              colorClass="text-loss"
              loading={analyticsLoading}
            />
            <MetricCard
              label="Payoff Ratio"
              value={analyticsLoading ? null : ratioStr(wl?.payoff_ratio ?? null)}
              colorClass={colorBand(wl?.payoff_ratio ?? null, 1.5, 1.0)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Largest Win"
              value={analyticsLoading ? null : rupeeStr(wl?.largest_win ?? null)}
              colorClass="text-gain"
              loading={analyticsLoading}
            />
            <MetricCard
              label="Largest Loss"
              value={analyticsLoading ? null : rupeeStr(wl?.largest_loss ?? null)}
              colorClass="text-loss"
              loading={analyticsLoading}
            />
          </div>

          {/* SECTION 3 — Risk Management */}
          <SectionLabel>Risk Management</SectionLabel>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="Max Drawdown"
              value={analyticsLoading ? null : pctStr(risk?.max_drawdown_pct ?? null)}
              tooltip="Largest peak-to-trough drop in your cumulative P&L. Lower is better."
              loading={analyticsLoading}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={analyticsLoading ? null : ratioStr(risk?.sharpe_ratio ?? null)}
              tooltip="Risk-adjusted return. Above 1.5 is good, above 2.0 is excellent."
              loading={analyticsLoading}
            />
            <MetricCard
              label="Sortino Ratio"
              value={analyticsLoading ? null : ratioStr(risk?.sortino_ratio ?? null)}
              tooltip="Like Sharpe but only penalizes losing days. More relevant for traders."
              loading={analyticsLoading}
            />
            <MetricCard
              label="Daily P&L Volatility"
              value={analyticsLoading ? null : rupeeStr(risk?.daily_pnl_volatility ?? null)}
              tooltip="Standard deviation of your daily P&L."
              loading={analyticsLoading}
            />
            <MetricCard
              label="Annualized Volatility"
              value={analyticsLoading ? null : rupeeStr(risk?.annualized_volatility ?? null)}
              tooltip="Standard deviation of your daily P&L."
              loading={analyticsLoading}
            />
            <MetricCard
              label="Risk per Trade"
              value={analyticsLoading ? null : pctStr(risk?.risk_per_trade_pct ?? null)}
              tooltip="Requires capital base — connect broker to calculate."
              subtitle={risk?.risk_per_trade_pct == null ? "Requires capital base" : undefined}
              loading={analyticsLoading}
            />
          </div>

          {/* SECTION 4 — Efficiency & Consistency */}
          <SectionLabel>Efficiency &amp; Consistency</SectionLabel>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="% Profitable Days"
              value={analyticsLoading ? null : pctStr(eff?.pct_profitable_days ?? null)}
              colorClass={colorBandNoRed(eff?.pct_profitable_days ?? null, 55, 45)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Avg Holding Days"
              value={analyticsLoading ? null : eff?.avg_holding_days != null ? eff.avg_holding_days.toFixed(1) : null}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Trades per Day"
              value={analyticsLoading ? null : eff?.trades_per_day_avg != null ? eff.trades_per_day_avg.toFixed(2) : null}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Total Trading Days"
              value={analyticsLoading ? null : eff ? String(eff.total_trading_days) : null}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Recovery Factor"
              value={analyticsLoading ? null : ratioStr(eff?.recovery_factor ?? null)}
              colorClass={colorBandNoRed(eff?.recovery_factor ?? null, 2.0, 1.0)}
              loading={analyticsLoading}
            />
            <MetricCard
              label="Total Trades"
              value={analyticsLoading ? null : eff ? String(eff.total_trades) : null}
              loading={analyticsLoading}
            />
          </div>

          {/* SECTION 5 — Equity Curve */}
          <SectionLabel>Equity Curve</SectionLabel>
          <Card className="mt-4 p-5">
            {analyticsLoading ? (
              <div className="h-[200px] animate-pulse rounded bg-rule" />
            ) : equityCurve && equityCurve.length > 0 ? (
              <EquityCurveChart data={equityCurve} />
            ) : (
              <p className="text-sm text-ink-faint">
                Not enough trade history to draw equity curve.
              </p>
            )}
          </Card>

          {/* SECTION 6 — Cost & Execution */}
          <SectionLabel>Cost &amp; Execution</SectionLabel>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MetricCard
              label="Transaction Costs"
              value={null}
              subtitle="Requires broker sync with charge data"
              loading={analyticsLoading}
            />
            <MetricCard
              label="Breakeven Win Rate"
              value={null}
              subtitle="Requires broker sync with charge data"
              loading={analyticsLoading}
            />
            <MetricCard
              label="Slippage"
              value={null}
              subtitle="Requires broker sync with charge data"
              loading={analyticsLoading}
            />
          </div>
        </>
      )}

      {/* ── Trade Notes (voice + text journal, secondary feature) ── */}
      <SectionLabel>Trade Notes</SectionLabel>
      <p className="mt-1 text-sm text-ink-muted">
        Record how you felt about a trade — reflection, not advice. Raw audio is
        transcribed and discarded immediately; only the text is kept.
      </p>

      <Card className="mt-4 p-5">
        <h2 className="mb-4 font-display text-base text-ink">New entry</h2>

        {!micUnsupported && (
          <div className="flex items-center gap-3">
            {!recording ? (
              <Button onClick={startRecording} disabled={transcribing}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <circle cx="12" cy="12" r="8" />
                </svg>
                Record
              </Button>
            ) : (
              <Button onClick={stopRecording} variant="secondary">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
                Stop &amp; transcribe
              </Button>
            )}
            {recording && (
              <Badge tone="loss">
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-loss" />
                  Recording
                </span>
              </Badge>
            )}
            {transcribing && <Badge tone="estimate">Transcribing…</Badge>}
          </div>
        )}

        <div className="mt-4 flex items-start gap-2">
          <textarea
            className={`${inputCls} h-20 resize-none`}
            placeholder="…or just type how you're feeling about a trade"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
          />
        </div>
        <div className="mt-2 flex justify-end">
          <Button
            variant="secondary"
            onClick={handleTextSubmit}
            loading={submittingText}
            className="h-8 px-3 text-xs"
          >
            Save entry
          </Button>
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )}
      </Card>

      {/* ── Tag the entry just created ── */}
      {pendingEntry && (
        <Card className="mt-4 p-5">
          <MetricLabel>Tag this entry (optional)</MetricLabel>
          <p className="mt-2 text-sm text-ink-muted italic">&ldquo;{pendingEntry.entry.transcript}&rdquo;</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(taxonomy).map(([tag, description]) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                title={description}
                className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  selectedTags.includes(tag)
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-rule text-ink-muted hover:text-ink"
                }`}
              >
                {tag.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setPendingEntry(null)} className="h-8 px-3 text-xs">
              Skip
            </Button>
            <Button onClick={handleSaveTags} loading={savingTags} className="h-8 px-3 text-xs">
              Save tags
            </Button>
          </div>
        </Card>
      )}

      {/* ── Entries list ── */}
      <div className="mt-6">
        <h2 className="mb-3 font-display text-lg text-ink">Past entries</h2>
        {loadingEntries ? (
          <p className="text-sm text-ink-faint">Loading…</p>
        ) : !entries || entries.length === 0 ? (
          <EmptyState
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="9" y="2" width="6" height="12" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <path d="M12 19v3" />
              </svg>
            }
            title="No journal entries yet"
            description="Record a voice note or type a quick reflection above to get started."
          />
        ) : (
          <div className="space-y-3">
            {entries.map(({ entry, tags }) => (
              <Card key={entry.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-ink">{entry.transcript}</p>
                    {tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {tags.map((t) => (
                          <Badge key={t.id} tone="brand">
                            {t.tag_name.replace(/_/g, " ")}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <p className="mt-2 text-xs text-ink-faint">{fmtDate(entry.created_at)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(entry.id)}
                    disabled={deletingId === entry.id}
                    className="shrink-0 cursor-pointer rounded p-1 text-ink-faint transition-colors hover:text-loss disabled:opacity-50"
                    aria-label="Delete entry"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6h16Z" />
                    </svg>
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Card className="mt-6 p-4">
        <p className="flex items-start gap-2 text-xs text-ink-muted">
          <Badge tone="estimate">Not financial advice</Badge>
          <span>
            This journal is for personal reflection only — it never suggests buy or
            sell decisions. Raw voice recordings are deleted immediately after
            transcription; only the text is kept. Delete any entry at any time.
          </span>
        </p>
      </Card>
    </div>
  );
}

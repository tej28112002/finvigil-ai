"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetch } from "@/lib/api";

// ── types ────────────────────────────────────────────────────────────────────

type Segment = "futures" | "options";
type Position = "buy" | "sell";
type OptionType = "CE" | "PE";
type Expiry = "weekly" | "next_weekly" | "monthly" | "next_monthly";
type StrikeType =
  | "atm" | "otm" | "itm" | "premium_range" | "closest_premium"
  | "premium_gte" | "straddle_width" | "pct_of_atm"
  | "synthetic_future" | "atm_premium_pct";
type SlTargetType = "points" | "percentage" | "trailing";
type OverallSlTargetType = "mtm" | "premium_pct";
type ReentryType = "re_asap" | "re_asap_reverse" | "re_momentum" | "re_momentum_reverse";

interface LegForm {
  segment: Segment;
  position: Position;
  quantity_lots: number;
  option_type: OptionType | null;
  expiry: Expiry | null;
  strike_type: StrikeType | null;
  strike_value: number | null;
  strike_value2: number | null;
  sl_enabled: boolean;
  sl_type: SlTargetType | null;
  sl_value: number | null;
  target_enabled: boolean;
  target_type: SlTargetType | null;
  target_value: number | null;
}

interface StrategyForm {
  name: string;
  instrument: string;
  underlying_from: "cash" | "futures";
  strategy_type: "intraday" | "btst" | "positional";
  entry_time: string;
  exit_time: string;
  no_reentry_after_enabled: boolean;
  no_reentry_after_time: string | null;
  overall_momentum_enabled: boolean;
  overall_momentum_direction: string | null;
  overall_momentum_type: string | null;
  overall_momentum_value: number | null;
  square_off: "partial" | "complete";
  trail_sl_to_breakeven: boolean;
  trail_sl_apply_to: "all" | "sl_legs" | null;
  overall_sl_enabled: boolean;
  overall_sl_type: OverallSlTargetType | null;
  overall_sl_value: number | null;
  overall_sl_reentry_type: ReentryType | null;
  overall_sl_max_reentries: number | null;
  overall_target_enabled: boolean;
  overall_target_type: OverallSlTargetType | null;
  overall_target_value: number | null;
  overall_target_reentry_type: ReentryType | null;
  overall_target_max_reentries: number | null;
  lock_profit_enabled: boolean;
  lock_profit_trigger: number | null;
  lock_profit_lock_at: number | null;
  lock_and_trail_enabled: boolean;
  lock_and_trail_trigger: number | null;
  lock_and_trail_lock_at: number | null;
  lock_and_trail_trail_by_gain: number | null;
  lock_and_trail_trail_by_amount: number | null;
  overall_trail_sl_enabled: boolean;
  overall_trail_sl_type: OverallSlTargetType | null;
  overall_trail_sl_gain: number | null;
  overall_trail_sl_move: number | null;
  start_date: string;
  end_date: string;
}

interface LegResponse extends LegForm {
  id: string;
  leg_order: number;
}

interface StrategyResponse extends StrategyForm {
  id: string;
  user_id: string;
  legs: LegResponse[];
}

interface EquityPoint {
  date: string;
  cumulative_pnl: number;
  daily_pnl: number;
}
interface BacktestSummary {
  net_profit: number;
  win_rate_pct: number;
  profit_factor: number | null;
  expectancy: number;
  max_drawdown_pct: number;
  sharpe_ratio: number | null;
  total_trades: number;
  total_days: number;
}
interface BacktestResult {
  status: "completed" | "insufficient_data" | "failed";
  message?: string;
  strategy_type?: string;
  legs_count?: number;
  date_range?: { start: string; end: string };
  summary?: BacktestSummary;
  equity_curve?: EquityPoint[];
  note?: string;
}
interface RunResponse {
  id: string;
  strategy_id: string;
  status: string;
  result_json: BacktestResult | null;
  error_message: string | null;
  created_at?: string;
}

// ── constants ────────────────────────────────────────────────────────────────

const INSTRUMENTS = ["NIFTY", "BANKNIFTY", "SENSEX", "MIDCPNIFTY", "FINNIFTY"];

const TABS = ["Instrument", "Entry", "Legwise", "Leg Builder", "Overall Strategy", "Duration"] as const;

const STRIKE_TYPE_OPTIONS: { value: StrikeType; label: string }[] = [
  { value: "atm", label: "ATM" },
  { value: "otm", label: "OTM (steps)" },
  { value: "itm", label: "ITM (steps)" },
  { value: "premium_range", label: "Premium Range" },
  { value: "closest_premium", label: "Closest Premium" },
  { value: "premium_gte", label: "Premium ≥" },
  { value: "straddle_width", label: "Straddle Width" },
  { value: "pct_of_atm", label: "% of ATM" },
  { value: "synthetic_future", label: "Synthetic Future" },
  { value: "atm_premium_pct", label: "ATM Premium %" },
];

const REENTRY_OPTIONS: { value: ReentryType | ""; label: string }[] = [
  { value: "", label: "None" },
  { value: "re_asap", label: "RE-ASAP" },
  { value: "re_asap_reverse", label: "RE-ASAP ↩" },
  { value: "re_momentum", label: "RE-Momentum" },
  { value: "re_momentum_reverse", label: "RE-Momentum ↩" },
];

function defaultForm(): StrategyForm {
  return {
    name: "My Strategy",
    instrument: "NIFTY",
    underlying_from: "cash",
    strategy_type: "intraday",
    entry_time: "09:20",
    exit_time: "15:15",
    no_reentry_after_enabled: false,
    no_reentry_after_time: null,
    overall_momentum_enabled: false,
    overall_momentum_direction: null,
    overall_momentum_type: null,
    overall_momentum_value: null,
    square_off: "partial",
    trail_sl_to_breakeven: false,
    trail_sl_apply_to: "all",
    overall_sl_enabled: false,
    overall_sl_type: null,
    overall_sl_value: null,
    overall_sl_reentry_type: null,
    overall_sl_max_reentries: 1,
    overall_target_enabled: false,
    overall_target_type: null,
    overall_target_value: null,
    overall_target_reentry_type: null,
    overall_target_max_reentries: 1,
    lock_profit_enabled: false,
    lock_profit_trigger: null,
    lock_profit_lock_at: null,
    lock_and_trail_enabled: false,
    lock_and_trail_trigger: null,
    lock_and_trail_lock_at: null,
    lock_and_trail_trail_by_gain: null,
    lock_and_trail_trail_by_amount: null,
    overall_trail_sl_enabled: false,
    overall_trail_sl_type: null,
    overall_trail_sl_gain: null,
    overall_trail_sl_move: null,
    start_date: "2024-01-01",
    end_date: new Date().toISOString().slice(0, 10),
  };
}

function defaultLeg(): LegForm {
  return {
    segment: "options",
    position: "sell",
    quantity_lots: 1,
    option_type: "CE",
    expiry: "weekly",
    strike_type: "atm",
    strike_value: null,
    strike_value2: null,
    sl_enabled: false,
    sl_type: null,
    sl_value: null,
    target_enabled: false,
    target_type: null,
    target_value: null,
  };
}

// ── small shared UI ──────────────────────────────────────────────────────────

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:opacity-50";

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-ink-muted">{children}</label>;
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex gap-1 rounded-md border border-rule bg-surface p-1">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`cursor-pointer rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              active ? "bg-brand text-brand-fg" : "text-ink-muted hover:text-ink"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
  label,
  disabled = false,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <label className={`inline-flex items-center gap-2 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
      <span
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? "bg-brand" : "bg-rule"
        } ${disabled ? "" : "cursor-pointer"}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface shadow-token-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
      {label && <span className="text-sm text-ink">{label}</span>}
    </label>
  );
}

function rupeeStr(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const sign = v < 0 ? "-" : "";
  return `${sign}₹${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
function pctStr(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(2)}%`;
}
function ratioStr(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(2);
}
function colorSign(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-ink-faint";
  if (v > 0) return "text-gain";
  if (v < 0) return "text-loss";
  return "text-ink";
}

function legSummary(leg: LegForm): string {
  const parts = [leg.position === "buy" ? "Buy" : "Sell"];
  if (leg.segment === "options") {
    if (leg.option_type) parts.push(leg.option_type);
    const strikeLabel = STRIKE_TYPE_OPTIONS.find((o) => o.value === leg.strike_type)?.label;
    if (strikeLabel) parts.push(strikeLabel);
    if (leg.expiry) parts.push(leg.expiry.replace(/_/g, " "));
  } else {
    parts.push("Futures");
  }
  if (leg.sl_enabled && leg.sl_value != null) {
    parts.push(`SL: ${leg.sl_value}${leg.sl_type === "percentage" ? "%" : ""}`);
  }
  if (leg.target_enabled && leg.target_value != null) {
    parts.push(`Target: ${leg.target_value}${leg.target_type === "percentage" ? "%" : ""}`);
  }
  return parts.join(" · ");
}

// strike types that need one extra numeric input, and its label
const STRIKE_EXTRA_LABEL: Partial<Record<StrikeType, string>> = {
  otm: "Steps",
  itm: "Steps",
  closest_premium: "Target premium",
  premium_gte: "Minimum premium",
  straddle_width: "Multiplier",
  pct_of_atm: "Percentage",
  atm_premium_pct: "Percentage",
};

// ── equity curve chart (hand-rolled SVG, no chart library) ────────────────────

function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (data.length < 3) {
    return <p className="text-sm text-ink-faint">Not enough trade history to draw equity curve.</p>;
  }

  const width = 800;
  const height = 220;
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
        <line x1={padding} y1={zeroY} x2={width - padding} y2={zeroY} stroke="var(--color-rule)" strokeDasharray="4 4" />
        <polyline points={polylinePoints} fill="none" stroke={lineColor} strokeWidth="2" />
        {hovered && (
          <>
            <line x1={hovered.x} y1={padding} x2={hovered.x} y2={height - padding} stroke="var(--color-rule)" strokeWidth="1" />
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
          <div className={`font-mono ${colorSign(hovered.cumulative_pnl)}`}>{rupeeStr(hovered.cumulative_pnl)}</div>
        </div>
      )}
      <div className="mt-2 flex justify-between text-xs text-ink-faint">
        <span>{data[0].date} · {rupeeStr(data[0].cumulative_pnl)}</span>
        <span>{data[data.length - 1].date} · {rupeeStr(data[data.length - 1].cumulative_pnl)}</span>
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function BacktestClient() {
  const [activeTab, setActiveTab] = useState(0);
  const [form, setForm] = useState<StrategyForm>(defaultForm());
  const [legs, setLegs] = useState<LegForm[]>([]);

  const [legFormOpen, setLegFormOpen] = useState(false);
  const [editingLegIndex, setEditingLegIndex] = useState<number | null>(null);
  const [draftLeg, setDraftLeg] = useState<LegForm>(defaultLeg());

  const [currentStrategyId, setCurrentStrategyId] = useState<string | null>(null);
  const [savedStrategies, setSavedStrategies] = useState<StrategyResponse[]>([]);

  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<RunResponse | null>(null);
  const [pastRuns, setPastRuns] = useState<RunResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  function refreshSavedStrategies() {
    apiFetch<StrategyResponse[]>("/backtest/strategies")
      .then(setSavedStrategies)
      .catch(() => setSavedStrategies([]));
  }

  useEffect(() => {
    refreshSavedStrategies();
  }, []);

  function patchForm(patch: Partial<StrategyForm>) {
    setForm((f) => ({ ...f, ...patch }));
  }

  // ── leg builder ──
  function openAddLeg() {
    setDraftLeg(defaultLeg());
    setEditingLegIndex(null);
    setLegFormOpen(true);
  }
  function openEditLeg(index: number) {
    setDraftLeg({ ...legs[index] });
    setEditingLegIndex(index);
    setLegFormOpen(true);
  }
  function saveLegDraft() {
    setLegs((prev) => {
      if (editingLegIndex !== null) {
        const next = [...prev];
        next[editingLegIndex] = draftLeg;
        return next;
      }
      return [...prev, draftLeg];
    });
    setLegFormOpen(false);
  }
  function deleteLeg(index: number) {
    setLegs((prev) => prev.filter((_, i) => i !== index));
  }

  // ── save / run / load ──
  async function saveStrategy(runAfter: boolean) {
    setError(null);
    setSaving(true);
    try {
      const payload = { ...form, legs };
      const path = currentStrategyId
        ? `/backtest/strategies/${currentStrategyId}`
        : "/backtest/strategies";
      const saved = await apiFetch<StrategyResponse>(path, {
        method: currentStrategyId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCurrentStrategyId(saved.id);
      refreshSavedStrategies();
      if (runAfter) {
        await runBacktest(saved.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save strategy.");
    } finally {
      setSaving(false);
    }
  }

  async function runBacktest(strategyId: string) {
    setRunning(true);
    setError(null);
    try {
      const run = await apiFetch<RunResponse>(`/backtest/strategies/${strategyId}/run`, {
        method: "POST",
      });
      setCurrentRun(run);
      const runs = await apiFetch<RunResponse[]>(`/backtest/strategies/${strategyId}/runs`);
      setPastRuns(runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run backtest.");
    } finally {
      setRunning(false);
    }
  }

  async function loadSavedStrategy(id: string) {
    if (!id) return;
    setError(null);
    try {
      const strategy = await apiFetch<StrategyResponse>(`/backtest/strategies/${id}`);
      setForm({
        ...strategy,
        entry_time: strategy.entry_time.slice(0, 5),
        exit_time: strategy.exit_time.slice(0, 5),
        no_reentry_after_time: strategy.no_reentry_after_time
          ? strategy.no_reentry_after_time.slice(0, 5)
          : null,
      } as StrategyForm);
      setLegs(strategy.legs.map((l) => ({ ...l })));
      setCurrentStrategyId(strategy.id);
      setCurrentRun(null);
      const runs = await apiFetch<RunResponse[]>(`/backtest/strategies/${id}/runs`);
      setPastRuns(runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load strategy.");
    }
  }

  function loadRun(run: RunResponse) {
    setCurrentRun(run);
  }

  const result = currentRun?.result_json ?? null;

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Strategy Backtester</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Build and simulate option strategies using historical trade data.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* LEFT — Strategy builder (40%) */}
        <div className="lg:col-span-2">
          <div className="flex flex-wrap gap-2" role="tablist">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={activeTab === i}
                onClick={() => setActiveTab(i)}
                className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  activeTab === i
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-rule text-ink-muted hover:border-rule-strong hover:text-ink"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-4">
            {/* TAB 1 — Instrument */}
            {activeTab === 0 && (
              <>
                <Card className="p-5">
                  <MetricLabel>Select instrument</MetricLabel>
                  <div className="mt-3 flex flex-wrap gap-1 rounded-md border border-rule bg-surface p-1">
                    {INSTRUMENTS.map((inst) => (
                      <button
                        key={inst}
                        type="button"
                        onClick={() => patchForm({ instrument: inst })}
                        className={`cursor-pointer rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                          form.instrument === inst ? "bg-brand text-brand-fg" : "text-ink-muted hover:text-ink"
                        }`}
                      >
                        {inst}
                      </button>
                    ))}
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Underlying from</MetricLabel>
                  <div className="mt-3">
                    <Segmented
                      options={[
                        { value: "cash", label: "Cash (spot price)" },
                        { value: "futures", label: "Futures (futures price)" },
                      ]}
                      value={form.underlying_from}
                      onChange={(v) => patchForm({ underlying_from: v })}
                    />
                  </div>
                </Card>
              </>
            )}

            {/* TAB 2 — Entry settings */}
            {activeTab === 1 && (
              <>
                <Card className="p-5">
                  <MetricLabel>Strategy type</MetricLabel>
                  <div className="mt-3">
                    <Segmented
                      options={[
                        { value: "intraday", label: "Intraday" },
                        { value: "btst", label: "BTST" },
                        { value: "positional", label: "Positional" },
                      ]}
                      value={form.strategy_type}
                      onChange={(v) => patchForm({ strategy_type: v })}
                    />
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Time controls</MetricLabel>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div>
                      <FieldLabel>Entry time</FieldLabel>
                      <input
                        type="time"
                        className={inputCls}
                        value={form.entry_time}
                        onChange={(e) => patchForm({ entry_time: e.target.value })}
                      />
                    </div>
                    <div>
                      <FieldLabel>Exit time</FieldLabel>
                      <input
                        type="time"
                        className={inputCls}
                        value={form.exit_time}
                        onChange={(e) => patchForm({ exit_time: e.target.value })}
                      />
                    </div>
                  </div>
                </Card>
                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>No re-entry after</MetricLabel>
                    <ToggleSwitch
                      checked={form.no_reentry_after_enabled}
                      onChange={(v) => patchForm({ no_reentry_after_enabled: v })}
                    />
                  </div>
                  {form.no_reentry_after_enabled && (
                    <div className="mt-3">
                      <FieldLabel>Cutoff time</FieldLabel>
                      <input
                        type="time"
                        className={inputCls}
                        value={form.no_reentry_after_time ?? ""}
                        onChange={(e) => patchForm({ no_reentry_after_time: e.target.value })}
                      />
                    </div>
                  )}
                </Card>
                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Overall momentum</MetricLabel>
                    <ToggleSwitch
                      checked={form.overall_momentum_enabled}
                      onChange={(v) => patchForm({ overall_momentum_enabled: v })}
                    />
                  </div>
                  {form.overall_momentum_enabled && (
                    <div className="mt-3 space-y-3">
                      <Segmented
                        options={[
                          { value: "up", label: "Up" },
                          { value: "down", label: "Down" },
                        ]}
                        value={form.overall_momentum_direction ?? "up"}
                        onChange={(v) => patchForm({ overall_momentum_direction: v })}
                      />
                      <Segmented
                        options={[
                          { value: "points", label: "Points" },
                          { value: "percentage", label: "Percentage" },
                        ]}
                        value={form.overall_momentum_type ?? "points"}
                        onChange={(v) => patchForm({ overall_momentum_type: v })}
                      />
                      <div>
                        <FieldLabel>Value</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.overall_momentum_value ?? ""}
                          onChange={(e) =>
                            patchForm({ overall_momentum_value: e.target.value === "" ? null : Number(e.target.value) })
                          }
                        />
                      </div>
                    </div>
                  )}
                </Card>
              </>
            )}

            {/* TAB 3 — Legwise settings */}
            {activeTab === 2 && (
              <>
                <Card className="p-5">
                  <MetricLabel>Square off</MetricLabel>
                  <div className="mt-3 space-y-2">
                    <label className="flex cursor-pointer items-start gap-2">
                      <input
                        type="radio"
                        className="mt-1"
                        checked={form.square_off === "partial"}
                        onChange={() => patchForm({ square_off: "partial" })}
                      />
                      <span className="text-sm text-ink">
                        <span className="font-medium">Partial</span> — Exit only the leg that hit SL/Target
                      </span>
                    </label>
                    <label className="flex cursor-pointer items-start gap-2">
                      <input
                        type="radio"
                        className="mt-1"
                        checked={form.square_off === "complete"}
                        onChange={() => patchForm({ square_off: "complete" })}
                      />
                      <span className="text-sm text-ink">
                        <span className="font-medium">Complete</span> — Exit ALL legs when any one hits
                      </span>
                    </label>
                  </div>
                </Card>
                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Trail SL to break-even</MetricLabel>
                    <ToggleSwitch
                      checked={form.trail_sl_to_breakeven}
                      onChange={(v) => patchForm({ trail_sl_to_breakeven: v })}
                    />
                  </div>
                  {form.trail_sl_to_breakeven && (
                    <div className="mt-3">
                      <FieldLabel>Apply to</FieldLabel>
                      <Segmented
                        options={[
                          { value: "all", label: "All legs" },
                          { value: "sl_legs", label: "SL legs only" },
                        ]}
                        value={form.trail_sl_apply_to ?? "all"}
                        onChange={(v) => patchForm({ trail_sl_apply_to: v })}
                      />
                    </div>
                  )}
                </Card>
              </>
            )}

            {/* TAB 4 — Leg builder */}
            {activeTab === 3 && (
              <Card className="p-5">
                <div className="flex items-center justify-between">
                  <MetricLabel>Legs ({legs.length}/10)</MetricLabel>
                </div>

                {legs.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-faint">No legs added yet.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {legs.map((leg, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between rounded-md border border-rule px-3 py-2"
                      >
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge tone={leg.position === "buy" ? "gain" : "loss"}>
                            {leg.position === "buy" ? "Buy" : "Sell"}
                          </Badge>
                          <span className="text-xs text-ink-muted">{legSummary(leg)}</span>
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            type="button"
                            onClick={() => openEditLeg(i)}
                            className="cursor-pointer rounded p-1 text-ink-faint hover:text-ink"
                            aria-label="Edit leg"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteLeg(i)}
                            className="cursor-pointer rounded p-1 text-ink-faint hover:text-loss"
                            aria-label="Delete leg"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M18 6 6 18M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {legs.length >= 10 && (
                  <p className="mt-3 text-xs text-loss">Maximum 10 legs reached.</p>
                )}

                {!legFormOpen && legs.length < 10 && (
                  <Button variant="secondary" className="mt-4" onClick={openAddLeg}>
                    + Add Leg
                  </Button>
                )}

                {legFormOpen && (
                  <div className="mt-4 space-y-3 rounded-md border border-rule p-4">
                    <div>
                      <FieldLabel>Segment</FieldLabel>
                      <Segmented
                        options={[
                          { value: "futures", label: "Futures" },
                          { value: "options", label: "Options" },
                        ]}
                        value={draftLeg.segment}
                        onChange={(v) => setDraftLeg((d) => ({ ...d, segment: v }))}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <FieldLabel>Quantity (lots)</FieldLabel>
                        <input
                          type="number"
                          min={1}
                          max={20}
                          className={inputCls}
                          value={draftLeg.quantity_lots}
                          onChange={(e) =>
                            setDraftLeg((d) => ({ ...d, quantity_lots: Number(e.target.value) || 1 }))
                          }
                        />
                      </div>
                      <div>
                        <FieldLabel>Position</FieldLabel>
                        <Segmented
                          options={[
                            { value: "buy", label: "Buy" },
                            { value: "sell", label: "Sell" },
                          ]}
                          value={draftLeg.position}
                          onChange={(v) => setDraftLeg((d) => ({ ...d, position: v }))}
                        />
                      </div>
                    </div>

                    {draftLeg.segment === "options" && (
                      <>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <FieldLabel>Option type</FieldLabel>
                            <Segmented
                              options={[
                                { value: "CE", label: "CE" },
                                { value: "PE", label: "PE" },
                              ]}
                              value={draftLeg.option_type ?? "CE"}
                              onChange={(v) => setDraftLeg((d) => ({ ...d, option_type: v }))}
                            />
                          </div>
                          <div>
                            <FieldLabel>Expiry</FieldLabel>
                            <select
                              className={inputCls}
                              value={draftLeg.expiry ?? "weekly"}
                              onChange={(e) => setDraftLeg((d) => ({ ...d, expiry: e.target.value as Expiry }))}
                            >
                              <option value="weekly">Weekly</option>
                              <option value="next_weekly">Next Weekly</option>
                              <option value="monthly">Monthly</option>
                              <option value="next_monthly">Next Monthly</option>
                            </select>
                          </div>
                        </div>

                        <div>
                          <FieldLabel>Strike criteria</FieldLabel>
                          <select
                            className={inputCls}
                            value={draftLeg.strike_type ?? "atm"}
                            onChange={(e) =>
                              setDraftLeg((d) => ({ ...d, strike_type: e.target.value as StrikeType }))
                            }
                          >
                            {STRIKE_TYPE_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>

                        {draftLeg.strike_type === "premium_range" ? (
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <FieldLabel>Min premium</FieldLabel>
                              <input
                                type="number"
                                className={inputCls}
                                value={draftLeg.strike_value ?? ""}
                                onChange={(e) =>
                                  setDraftLeg((d) => ({
                                    ...d,
                                    strike_value: e.target.value === "" ? null : Number(e.target.value),
                                  }))
                                }
                              />
                            </div>
                            <div>
                              <FieldLabel>Max premium</FieldLabel>
                              <input
                                type="number"
                                className={inputCls}
                                value={draftLeg.strike_value2 ?? ""}
                                onChange={(e) =>
                                  setDraftLeg((d) => ({
                                    ...d,
                                    strike_value2: e.target.value === "" ? null : Number(e.target.value),
                                  }))
                                }
                              />
                            </div>
                          </div>
                        ) : (
                          draftLeg.strike_type &&
                          STRIKE_EXTRA_LABEL[draftLeg.strike_type] && (
                            <div>
                              <FieldLabel>{STRIKE_EXTRA_LABEL[draftLeg.strike_type]}</FieldLabel>
                              <input
                                type="number"
                                className={inputCls}
                                value={draftLeg.strike_value ?? ""}
                                onChange={(e) =>
                                  setDraftLeg((d) => ({
                                    ...d,
                                    strike_value: e.target.value === "" ? null : Number(e.target.value),
                                  }))
                                }
                              />
                            </div>
                          )
                        )}
                      </>
                    )}

                    <div className="border-t border-rule pt-3">
                      <div className="flex items-center justify-between">
                        <FieldLabel>Stop loss</FieldLabel>
                        <ToggleSwitch
                          checked={draftLeg.sl_enabled}
                          onChange={(v) => setDraftLeg((d) => ({ ...d, sl_enabled: v }))}
                        />
                      </div>
                      {draftLeg.sl_enabled && (
                        <div className="mt-2 grid grid-cols-2 gap-3">
                          <select
                            className={inputCls}
                            value={draftLeg.sl_type ?? "percentage"}
                            onChange={(e) => setDraftLeg((d) => ({ ...d, sl_type: e.target.value as SlTargetType }))}
                          >
                            <option value="points">Points</option>
                            <option value="percentage">Percentage</option>
                            <option value="trailing">Trailing SL</option>
                          </select>
                          <input
                            type="number"
                            placeholder="Value"
                            className={inputCls}
                            value={draftLeg.sl_value ?? ""}
                            onChange={(e) =>
                              setDraftLeg((d) => ({
                                ...d,
                                sl_value: e.target.value === "" ? null : Number(e.target.value),
                              }))
                            }
                          />
                        </div>
                      )}
                    </div>

                    <div className="border-t border-rule pt-3">
                      <div className="flex items-center justify-between">
                        <FieldLabel>Target</FieldLabel>
                        <ToggleSwitch
                          checked={draftLeg.target_enabled}
                          onChange={(v) => setDraftLeg((d) => ({ ...d, target_enabled: v }))}
                        />
                      </div>
                      {draftLeg.target_enabled && (
                        <div className="mt-2 grid grid-cols-2 gap-3">
                          <select
                            className={inputCls}
                            value={draftLeg.target_type ?? "percentage"}
                            onChange={(e) => setDraftLeg((d) => ({ ...d, target_type: e.target.value as SlTargetType }))}
                          >
                            <option value="points">Points</option>
                            <option value="percentage">Percentage</option>
                          </select>
                          <input
                            type="number"
                            placeholder="Value"
                            className={inputCls}
                            value={draftLeg.target_value ?? ""}
                            onChange={(e) =>
                              setDraftLeg((d) => ({
                                ...d,
                                target_value: e.target.value === "" ? null : Number(e.target.value),
                              }))
                            }
                          />
                        </div>
                      )}
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => setLegFormOpen(false)}>
                        Cancel
                      </Button>
                      <Button className="h-8 px-3 text-xs" onClick={saveLegDraft}>
                        Add this leg
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* TAB 5 — Overall strategy settings */}
            {activeTab === 4 && (
              <>
                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Overall Stop Loss</MetricLabel>
                    <ToggleSwitch
                      checked={form.overall_sl_enabled}
                      onChange={(v) => patchForm({ overall_sl_enabled: v })}
                    />
                  </div>
                  {form.overall_sl_enabled && (
                    <div className="mt-3 space-y-3">
                      <Segmented
                        options={[
                          { value: "mtm", label: "MTM (₹ amount)" },
                          { value: "premium_pct", label: "Total Premium %" },
                        ]}
                        value={form.overall_sl_type ?? "mtm"}
                        onChange={(v) => patchForm({ overall_sl_type: v })}
                      />
                      <input
                        type="number"
                        placeholder="Value"
                        className={inputCls}
                        value={form.overall_sl_value ?? ""}
                        onChange={(e) =>
                          patchForm({ overall_sl_value: e.target.value === "" ? null : Number(e.target.value) })
                        }
                      />
                      <div>
                        <FieldLabel>Re-entry</FieldLabel>
                        <select
                          className={inputCls}
                          value={form.overall_sl_reentry_type ?? ""}
                          onChange={(e) =>
                            patchForm({
                              overall_sl_reentry_type: (e.target.value || null) as ReentryType | null,
                            })
                          }
                        >
                          {REENTRY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      {form.overall_sl_reentry_type && (
                        <div>
                          <FieldLabel>Max re-entries</FieldLabel>
                          <select
                            className={inputCls}
                            value={form.overall_sl_max_reentries ?? 1}
                            onChange={(e) => patchForm({ overall_sl_max_reentries: Number(e.target.value) })}
                          >
                            {[1, 2, 3, 4, 5].map((n) => (
                              <option key={n} value={n}>
                                {n}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  )}
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Overall Target</MetricLabel>
                    <ToggleSwitch
                      checked={form.overall_target_enabled}
                      onChange={(v) => patchForm({ overall_target_enabled: v })}
                    />
                  </div>
                  {form.overall_target_enabled && (
                    <div className="mt-3 space-y-3">
                      <Segmented
                        options={[
                          { value: "mtm", label: "MTM (₹ amount)" },
                          { value: "premium_pct", label: "Total Premium %" },
                        ]}
                        value={form.overall_target_type ?? "mtm"}
                        onChange={(v) => patchForm({ overall_target_type: v })}
                      />
                      <input
                        type="number"
                        placeholder="Value"
                        className={inputCls}
                        value={form.overall_target_value ?? ""}
                        onChange={(e) =>
                          patchForm({ overall_target_value: e.target.value === "" ? null : Number(e.target.value) })
                        }
                      />
                      <div>
                        <FieldLabel>Re-entry</FieldLabel>
                        <select
                          className={inputCls}
                          value={form.overall_target_reentry_type ?? ""}
                          onChange={(e) =>
                            patchForm({
                              overall_target_reentry_type: (e.target.value || null) as ReentryType | null,
                            })
                          }
                        >
                          {REENTRY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      {form.overall_target_reentry_type && (
                        <div>
                          <FieldLabel>Max re-entries</FieldLabel>
                          <select
                            className={inputCls}
                            value={form.overall_target_max_reentries ?? 1}
                            onChange={(e) => patchForm({ overall_target_max_reentries: Number(e.target.value) })}
                          >
                            {[1, 2, 3, 4, 5].map((n) => (
                              <option key={n} value={n}>
                                {n}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  )}
                </Card>

                <h3 className="mt-2 text-sm font-medium text-ink-muted">Trailing Options</h3>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Lock Profit</MetricLabel>
                    <ToggleSwitch
                      checked={form.lock_profit_enabled}
                      onChange={(v) => patchForm({ lock_profit_enabled: v })}
                    />
                  </div>
                  {form.lock_profit_enabled && (
                    <div className="mt-3 grid grid-cols-2 gap-3">
                      <div>
                        <FieldLabel>If profit reaches (₹)</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_profit_trigger ?? ""}
                          onChange={(e) =>
                            patchForm({ lock_profit_trigger: e.target.value === "" ? null : Number(e.target.value) })
                          }
                        />
                      </div>
                      <div>
                        <FieldLabel>Lock at least (₹)</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_profit_lock_at ?? ""}
                          onChange={(e) =>
                            patchForm({ lock_profit_lock_at: e.target.value === "" ? null : Number(e.target.value) })
                          }
                        />
                      </div>
                    </div>
                  )}
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>Lock &amp; Trail</MetricLabel>
                    <ToggleSwitch
                      checked={form.lock_and_trail_enabled}
                      onChange={(v) => patchForm({ lock_and_trail_enabled: v })}
                    />
                  </div>
                  {form.lock_and_trail_enabled && (
                    <div className="mt-3 grid grid-cols-2 gap-3">
                      <div>
                        <FieldLabel>If profit reaches (₹)</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_and_trail_trigger ?? ""}
                          onChange={(e) =>
                            patchForm({ lock_and_trail_trigger: e.target.value === "" ? null : Number(e.target.value) })
                          }
                        />
                      </div>
                      <div>
                        <FieldLabel>Lock at (₹)</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_and_trail_lock_at ?? ""}
                          onChange={(e) =>
                            patchForm({ lock_and_trail_lock_at: e.target.value === "" ? null : Number(e.target.value) })
                          }
                        />
                      </div>
                      <div>
                        <FieldLabel>For every ₹ gain</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_and_trail_trail_by_gain ?? ""}
                          onChange={(e) =>
                            patchForm({
                              lock_and_trail_trail_by_gain: e.target.value === "" ? null : Number(e.target.value),
                            })
                          }
                        />
                      </div>
                      <div>
                        <FieldLabel>Trail by ₹ amount</FieldLabel>
                        <input
                          type="number"
                          className={inputCls}
                          value={form.lock_and_trail_trail_by_amount ?? ""}
                          onChange={(e) =>
                            patchForm({
                              lock_and_trail_trail_by_amount: e.target.value === "" ? null : Number(e.target.value),
                            })
                          }
                        />
                      </div>
                    </div>
                  )}
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <MetricLabel>
                      Overall Trail SL
                      {!form.overall_sl_enabled && (
                        <span className="ml-1 font-normal text-ink-faint">(requires Overall SL)</span>
                      )}
                    </MetricLabel>
                    <ToggleSwitch
                      checked={form.overall_trail_sl_enabled}
                      onChange={(v) => patchForm({ overall_trail_sl_enabled: v })}
                      disabled={!form.overall_sl_enabled}
                    />
                  </div>
                  {form.overall_trail_sl_enabled && form.overall_sl_enabled && (
                    <div className="mt-3 space-y-3">
                      <Segmented
                        options={[
                          { value: "mtm", label: "MTM" },
                          { value: "premium_pct", label: "Premium %" },
                        ]}
                        value={form.overall_trail_sl_type ?? "mtm"}
                        onChange={(v) => patchForm({ overall_trail_sl_type: v })}
                      />
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <FieldLabel>For every ₹ gain</FieldLabel>
                          <input
                            type="number"
                            className={inputCls}
                            value={form.overall_trail_sl_gain ?? ""}
                            onChange={(e) =>
                              patchForm({ overall_trail_sl_gain: e.target.value === "" ? null : Number(e.target.value) })
                            }
                          />
                        </div>
                        <div>
                          <FieldLabel>Move SL by ₹</FieldLabel>
                          <input
                            type="number"
                            className={inputCls}
                            value={form.overall_trail_sl_move ?? ""}
                            onChange={(e) =>
                              patchForm({ overall_trail_sl_move: e.target.value === "" ? null : Number(e.target.value) })
                            }
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </Card>
              </>
            )}

            {/* TAB 6 — Duration */}
            {activeTab === 5 && (
              <Card className="p-5">
                <MetricLabel>Backtest period</MetricLabel>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <FieldLabel>Start date</FieldLabel>
                    <input
                      type="date"
                      className={inputCls}
                      value={form.start_date}
                      onChange={(e) => patchForm({ start_date: e.target.value })}
                    />
                  </div>
                  <div>
                    <FieldLabel>End date</FieldLabel>
                    <input
                      type="date"
                      className={inputCls}
                      value={form.end_date}
                      onChange={(e) => patchForm({ end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mt-4 rounded-md border border-brand-soft bg-brand-soft/40 px-3 py-2.5 text-xs text-ink-muted">
                  The engine simulates your strategy against realized trade data in this
                  date range. F&amp;O historical data (1-minute OHLC) integration is
                  coming soon &mdash; strategy parameters will apply once available.
                </div>
              </Card>
            )}
          </div>

          {/* Bottom of left panel */}
          <Card className="mt-6 p-5">
            <FieldLabel>Strategy name</FieldLabel>
            <input
              type="text"
              className={inputCls}
              value={form.name}
              onChange={(e) => patchForm({ name: e.target.value })}
            />
            <div className="mt-3 flex gap-2">
              <Button variant="secondary" loading={saving && !running} onClick={() => saveStrategy(false)}>
                Save Strategy
              </Button>
              <Button loading={saving || running} onClick={() => saveStrategy(true)}>
                Run Backtest
              </Button>
            </div>

            {savedStrategies.length > 0 && (
              <div className="mt-4">
                <FieldLabel>Saved strategies</FieldLabel>
                <select
                  className={inputCls}
                  value={currentStrategyId ?? ""}
                  onChange={(e) => loadSavedStrategy(e.target.value)}
                >
                  <option value="">Load a saved strategy&hellip;</option>
                  {savedStrategies.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </Card>
        </div>

        {/* RIGHT — Results panel (60%) */}
        <div className="lg:col-span-3">
          {running ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                {[0, 1, 2, 3, 4, 5].map((i) => (
                  <Card key={i} className="p-5">
                    <div className="h-3 w-20 animate-pulse rounded bg-rule" />
                    <div className="mt-3 h-8 w-24 animate-pulse rounded bg-rule" />
                  </Card>
                ))}
              </div>
              <Card className="p-5">
                <div className="h-[220px] animate-pulse rounded bg-rule" />
              </Card>
            </div>
          ) : !result ? (
            <Card className="p-5">
              <EmptyState
                icon={
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M3 3v18h18" />
                    <path d="m7 14 4-4 3 3 5-6" />
                  </svg>
                }
                title="No backtest run yet"
                description="Configure your strategy on the left and click Run Backtest to see results."
              />
            </Card>
          ) : result.status === "insufficient_data" ? (
            <Card className="border-estimate/30 bg-estimate-soft p-5">
              <div className="flex items-start gap-3">
                <span className="text-lg">⚠</span>
                <div>
                  <p className="font-display text-base text-ink">
                    {result.strategy_type === "options" ? "F&O Simulation Pending" : "Not Enough Data"}
                  </p>
                  <p className="mt-1 text-sm text-ink-muted">{result.message}</p>
                  <p className="mt-2 text-xs text-ink-faint">
                    Your strategy has been saved. We&rsquo;ll notify you when F&amp;O
                    historical data is available.
                  </p>
                </div>
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md border border-brand-soft bg-brand-soft/40 px-4 py-2.5 text-sm text-ink-muted">
                Equity simulation &mdash; based on your realized gains{" "}
                {result.date_range?.start} to {result.date_range?.end}. F&amp;O
                strategy parameters will apply once historical options data is
                integrated.
              </div>

              <h2 className="font-display text-lg text-ink">Summary</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <Card className="p-5">
                  <MetricLabel>Net P&amp;L</MetricLabel>
                  <div className="mt-3">
                    <span className={`font-mono text-2xl font-medium ${colorSign(result.summary?.net_profit)}`}>
                      {rupeeStr(result.summary?.net_profit)}
                    </span>
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Win Rate</MetricLabel>
                  <div className="mt-3">
                    <span className="font-mono text-2xl font-medium text-ink">
                      {pctStr(result.summary?.win_rate_pct)}
                    </span>
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Profit Factor</MetricLabel>
                  <div className="mt-3">
                    <span className="font-mono text-2xl font-medium text-ink">
                      {ratioStr(result.summary?.profit_factor)}
                    </span>
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Max Drawdown</MetricLabel>
                  <div className="mt-3">
                    <span className="font-mono text-2xl font-medium text-ink">
                      {pctStr(result.summary?.max_drawdown_pct)}
                    </span>
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Sharpe Ratio</MetricLabel>
                  <div className="mt-3">
                    <span className="font-mono text-2xl font-medium text-ink">
                      {ratioStr(result.summary?.sharpe_ratio)}
                    </span>
                  </div>
                </Card>
                <Card className="p-5">
                  <MetricLabel>Total Trades</MetricLabel>
                  <div className="mt-3">
                    <span className="font-mono text-2xl font-medium text-ink">
                      {result.summary?.total_trades ?? "—"}
                    </span>
                  </div>
                </Card>
              </div>

              <h2 className="font-display text-lg text-ink">Equity Curve</h2>
              <Card className="p-5">
                {result.equity_curve && result.equity_curve.length > 0 ? (
                  <EquityCurveChart data={result.equity_curve} />
                ) : (
                  <p className="text-sm text-ink-faint">Not enough trade history to draw equity curve.</p>
                )}
              </Card>
            </div>
          )}

          {pastRuns.length > 0 && (
            <div className="mt-6">
              <h2 className="mb-3 font-display text-lg text-ink">Past Runs</h2>
              <Card className="overflow-x-auto p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-rule text-left text-xs text-ink-muted">
                      <th className="px-4 py-2 font-medium">Run date</th>
                      <th className="px-4 py-2 font-medium">Status</th>
                      <th className="px-4 py-2 font-medium">Net P&amp;L</th>
                      <th className="px-4 py-2 font-medium">Trades</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pastRuns.map((run) => (
                      <tr
                        key={run.id}
                        onClick={() => loadRun(run)}
                        className="cursor-pointer border-b border-rule last:border-0 hover:bg-brand-soft/30"
                      >
                        <td className="px-4 py-2 text-ink-muted">
                          {run.created_at ? new Date(run.created_at).toLocaleString("en-IN") : "—"}
                        </td>
                        <td className="px-4 py-2">
                          <Badge
                            tone={
                              run.status === "completed"
                                ? "gain"
                                : run.status === "failed"
                                  ? "loss"
                                  : "estimate"
                            }
                          >
                            {run.status}
                          </Badge>
                        </td>
                        <td className={`px-4 py-2 font-mono ${colorSign(run.result_json?.summary?.net_profit)}`}>
                          {rupeeStr(run.result_json?.summary?.net_profit)}
                        </td>
                        <td className="px-4 py-2 font-mono text-ink">
                          {run.result_json?.summary?.total_trades ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

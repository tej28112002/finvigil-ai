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
  drawdown: number;
}
interface BacktestSummary {
  overall_profit: number;
  total_trades: number;
  avg_profit_per_trade: number;
  win_pct: number;
  loss_pct: number;
  avg_profit_on_winning: number;
  avg_loss_on_losing: number;
  max_profit_single_trade: number;
  max_loss_single_trade: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number;
  max_drawdown_start: string | null;
  max_drawdown_end: string | null;
  return_over_max_dd: number | null;
  reward_to_risk_ratio: number | null;
  expectancy_ratio: number;
  max_win_streak: number;
  max_losing_streak: number;
  sharpe_ratio: number | null;
}
interface YearlyReturn {
  year: number;
  jan: number | null; feb: number | null; mar: number | null; apr: number | null;
  may: number | null; jun: number | null; jul: number | null; aug: number | null;
  sep: number | null; oct: number | null; nov: number | null; dec: number | null;
  total: number;
  max_drawdown: number;
  days_for_mdd: number | null;
  return_over_mdd: number | null;
}
interface TradeRow {
  index: number;
  entry_date: string | null;
  exit_date: string;
  symbol: string;
  gain_type: string | null;
  quantity: number;
  entry_price: number;
  exit_price: number;
  holding_days: number;
  pnl: number;
}
interface BacktestResult {
  status: "completed" | "insufficient_data" | "failed";
  message?: string;
  strategy_type?: string;
  legs_count?: number;
  date_range?: { start: string; end: string };
  summary?: BacktestSummary;
  yearly_returns?: YearlyReturn[];
  equity_curve?: EquityPoint[];
  trades?: TradeRow[];
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

const MONTH_KEYS: (keyof YearlyReturn)[] = [
  "jan", "feb", "mar", "apr", "may", "jun",
  "jul", "aug", "sep", "oct", "nov", "dec",
];
const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

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

function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h2 className="font-display text-lg font-semibold text-ink">{children}</h2>;
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
    <div className="inline-flex flex-wrap gap-1 rounded-md border border-rule bg-surface p-1">
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

function InfoTip({ text }: { text: string }) {
  return (
    <span title={text} className="cursor-help text-ink-faint" aria-label="Info">
      {" "}ⓘ
    </span>
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

// A label + right-aligned value stat row (AlgoTest-style).
function StatRow({
  label,
  value,
  colorClass = "text-ink",
}: {
  label: string;
  value: string;
  colorClass?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-ink-muted">{label}</span>
      <span className={`font-mono font-medium ${colorClass}`}>{value}</span>
    </div>
  );
}

// ── dual-panel equity + drawdown chart (hand-rolled SVG, no chart library) ────

function formatAxisRupee(v: number): string {
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  if (abs >= 100000) {
    const lakhs = abs / 100000;
    return `${sign}₹${lakhs % 1 === 0 ? lakhs.toFixed(0) : lakhs.toFixed(1)}L`;
  }
  if (abs >= 1000) {
    const thousands = abs / 1000;
    return `${sign}₹${thousands % 1 === 0 ? thousands.toFixed(0) : thousands.toFixed(1)}K`;
  }
  return `${sign}₹${abs.toFixed(0)}`;
}

function formatAxisDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

function niceTicks(min: number, max: number, count: number): number[] {
  if (min === max) return [min];
  const step = (max - min) / (count - 1);
  return Array.from({ length: count }, (_, i) => min + step * i);
}

function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (data.length < 3) {
    return <p className="text-sm text-ink-faint">Not enough trade history to draw equity curve.</p>;
  }

  const width = 800;
  const padTop = 20;
  const padX = 56;
  const padRight = 16;
  const topH = 200;
  const gap = 30;
  const botH = 120;
  const padBottom = 22;
  const totalH = padTop + topH + gap + botH + padBottom;

  const cumVals = data.map((d) => d.cumulative_pnl);
  const ddVals = data.map((d) => d.drawdown);

  const cumMin = Math.min(...cumVals, 0);
  const cumMax = Math.max(...cumVals, 0);
  const cumRange = cumMax - cumMin || 1;

  const ddMin = Math.min(...ddVals, 0);
  const ddRange = 0 - ddMin || 1;

  const plotWidth = width - padX - padRight;
  const xStep = data.length > 1 ? plotWidth / (data.length - 1) : 0;
  const xAt = (i: number) => padX + i * xStep;

  const topYAt = (v: number) => padTop + (1 - (v - cumMin) / cumRange) * topH;
  const topZeroY = topYAt(0);

  const botTop = padTop + topH + gap;
  const botYAt = (v: number) => botTop + (1 - (v - ddMin) / ddRange) * botH;
  const botZeroY = botYAt(0);

  const isPositive = cumVals[cumVals.length - 1] >= 0;
  const cumColor = isPositive ? "var(--color-gain)" : "var(--color-loss)";

  const cumLine = data.map((d, i) => `${xAt(i)},${topYAt(d.cumulative_pnl)}`).join(" ");
  const ddLine = data.map((d, i) => `${xAt(i)},${botYAt(d.drawdown)}`).join(" ");

  const cumTicks = niceTicks(cumMin, cumMax, 5);
  const ddTicks = niceTicks(ddMin, 0, 4);

  function handleMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * width;
    let nearest = 0;
    let minDist = Infinity;
    data.forEach((_, i) => {
      const dist = Math.abs(xAt(i) - relX);
      if (dist < minDist) {
        minDist = dist;
        nearest = i;
      }
    });
    setHoverIdx(nearest);
  }

  const hovered = hoverIdx !== null ? data[hoverIdx] : null;
  const hoveredX = hoverIdx !== null ? xAt(hoverIdx) : 0;

  // 4-6 evenly spaced x-axis date labels, shown once below the bottom panel.
  const xLabelStep = Math.max(1, Math.floor((data.length - 1) / 5));
  const xLabels = data.filter((_, i) => i % xLabelStep === 0 || i === data.length - 1);

  return (
    <div className="rounded-md border border-rule bg-surface p-3">
      {/* legend */}
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "var(--color-gain)" }} aria-hidden="true" />
          <span className="text-ink-muted">Cumulative P&amp;L</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "var(--color-brand)" }} aria-hidden="true" />
          <span className="text-ink-muted">Underlying Value</span>
          <Badge tone="neutral">Coming soon</Badge>
        </span>
      </div>

      <div className="relative overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${totalH}`}
          width="100%"
          height={totalH}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverIdx(null)}
          className="min-w-[640px]"
        >
          {/* top panel: cumulative P&L — subtle gridlines + Y-axis labels */}
          {cumTicks.map((t, i) => (
            <g key={`cum-tick-${i}`}>
              <line
                x1={padX}
                y1={topYAt(t)}
                x2={width - padRight}
                y2={topYAt(t)}
                stroke="var(--color-ink-faint)"
                strokeOpacity="0.1"
              />
              <text x={padX - 6} y={topYAt(t) + 3} textAnchor="end" className="fill-[var(--color-ink-faint)] text-[9px]">
                {formatAxisRupee(t)}
              </text>
            </g>
          ))}
          <text x={padX} y={12} className="fill-[var(--color-ink-muted)] text-[11px]">Cumulative P&amp;L</text>
          <line x1={padX} y1={topZeroY} x2={width - padRight} y2={topZeroY} stroke="var(--color-rule)" strokeDasharray="4 4" />
          <polyline points={cumLine} fill="none" stroke={cumColor} strokeWidth="2" />

          {/* bottom panel: drawdown — clean red line, no fill */}
          {ddTicks.map((t, i) => (
            <g key={`dd-tick-${i}`}>
              <line
                x1={padX}
                y1={botYAt(t)}
                x2={width - padRight}
                y2={botYAt(t)}
                stroke="var(--color-ink-faint)"
                strokeOpacity="0.1"
              />
              <text x={padX - 6} y={botYAt(t) + 3} textAnchor="end" className="fill-[var(--color-ink-faint)] text-[9px]">
                {formatAxisRupee(t)}
              </text>
            </g>
          ))}
          <text x={padX} y={botTop - 8} className="fill-[var(--color-ink-muted)] text-[11px]">Drawdown</text>
          <line x1={padX} y1={botZeroY} x2={width - padRight} y2={botZeroY} stroke="var(--color-rule)" strokeDasharray="4 4" />
          <polyline points={ddLine} fill="none" stroke="var(--color-loss)" strokeWidth="1.5" />

          {/* shared x-axis date labels — once, below the bottom panel */}
          {xLabels.map((d) => {
            const i = data.indexOf(d);
            return (
              <text
                key={d.date}
                x={xAt(i)}
                y={totalH - 4}
                textAnchor="middle"
                className="fill-[var(--color-ink-faint)] text-[9px]"
              >
                {formatAxisDate(d.date)}
              </text>
            );
          })}

          {/* hover crosshair spanning both panels */}
          {hovered && (
            <>
              <line
                x1={hoveredX}
                y1={padTop}
                x2={hoveredX}
                y2={botTop + botH}
                stroke="var(--color-rule-strong)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle cx={hoveredX} cy={topYAt(hovered.cumulative_pnl)} r="3.5" fill={cumColor} />
              <circle cx={hoveredX} cy={botYAt(hovered.drawdown)} r="3.5" fill="var(--color-loss)" />
            </>
          )}
        </svg>
        {hovered && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-md border border-rule bg-surface px-2 py-1 text-xs shadow-token-sm"
            style={{ left: `${(hoveredX / width) * 100}%`, top: 0 }}
          >
            <div className="text-ink-muted">Date: {hovered.date}</div>
            <div className={`font-mono ${colorSign(hovered.cumulative_pnl)}`}>
              Cumulative P&amp;L: {rupeeStr(hovered.cumulative_pnl)}
            </div>
            <div className="font-mono text-loss">Drawdown: {rupeeStr(hovered.drawdown)}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── results panel ─────────────────────────────────────────────────────────────

const F_AND_O_DISCLAIMER =
  "Following results are backtested on equity trade data. These historical " +
  "simulations do not represent actual trading and have not been executed " +
  "in the live market.";

function ResultsHeader() {
  return (
    <div>
      <h2 className="font-display text-xl font-semibold tracking-wide text-ink">BACKTEST RESULT</h2>
      <div className="mt-2 rounded-md border border-estimate/30 bg-estimate-soft px-4 py-2.5 text-xs text-ink-muted">
        {F_AND_O_DISCLAIMER}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge tone="brand">Equity simulation</Badge>
        <Badge tone="neutral">Realized gains only</Badge>
        <Badge tone="estimate">F&amp;O: coming soon</Badge>
      </div>
    </div>
  );
}

// Include Brokerage / Taxes & charges / Slippage / VIX range — all display
// only for now, none of these feed into the computation yet. Every control
// here gives explicit "coming soon" feedback on interaction rather than
// silently doing nothing, so it can't be mistaken for a working control.
const RECALC_TOOLTIP =
  "Recalculation with brokerage/slippage coming soon once F&O data is integrated.";
const NOT_WIRED_MSG = "This will apply once F&O historical data is integrated.";

function FilterRecalcRow() {
  const [includeBrokerage, setIncludeBrokerage] = useState(false);
  const [taxesCharges, setTaxesCharges] = useState(false);
  const [slippagePct, setSlippagePct] = useState(0);
  const [vixFrom, setVixFrom] = useState(0);
  const [vixTo, setVixTo] = useState(150);
  const [brokerageMsg, setBrokerageMsg] = useState<string | null>(null);
  const [taxesMsg, setTaxesMsg] = useState<string | null>(null);

  return (
    <Card className="p-5">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        {/* LEFT */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-2">
              <FieldLabel>Include Brokerage</FieldLabel>
              <ToggleSwitch
                checked={includeBrokerage}
                onChange={(v) => {
                  setIncludeBrokerage(v);
                  setBrokerageMsg(v ? NOT_WIRED_MSG : null);
                }}
              />
            </div>
            {includeBrokerage ? (
              <input type="text" disabled value="0" className={`${inputCls} mt-1 w-24`} />
            ) : (
              <p className="mt-1 text-xs text-ink-faint">0</p>
            )}
            {brokerageMsg && <p className="mt-1 text-xs text-ink-faint">{brokerageMsg}</p>}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <FieldLabel>
                Taxes &amp; charges
                <InfoTip text="Taxes & charges will compute once broker integration provides transaction-level data." />
              </FieldLabel>
              <ToggleSwitch
                checked={taxesCharges}
                onChange={(v) => {
                  setTaxesCharges(v);
                  setTaxesMsg(v ? NOT_WIRED_MSG : null);
                }}
              />
            </div>
            <p className="mt-1 text-xs text-ink-faint">₹ 0</p>
            {taxesMsg && <p className="mt-1 text-xs text-ink-faint">{taxesMsg}</p>}
          </div>

          <div>
            <FieldLabel>
              Slippage (in %)
              <InfoTip text="Slippage simulates the difference between expected and actual fill price as a % of trade value." />
            </FieldLabel>
            <div className="mt-1 flex items-center gap-2">
              <input
                type="number"
                className={`${inputCls} w-24`}
                value={slippagePct}
                onChange={(e) => setSlippagePct(Number(e.target.value) || 0)}
              />
              <Button
                variant="secondary"
                className="h-8 px-3 text-xs"
                disabled
                title={RECALC_TOOLTIP}
              >
                Re-calculate
              </Button>
            </div>
            <p className="mt-1 text-xs text-ink-faint">{RECALC_TOOLTIP}</p>
          </div>
        </div>

        {/* RIGHT */}
        <div>
          <FieldLabel>Select VIX Range</FieldLabel>
          <div className="mt-1 flex items-center gap-2">
            <input
              type="number"
              className={`${inputCls} w-20`}
              value={vixFrom}
              onChange={(e) => setVixFrom(Number(e.target.value) || 0)}
            />
            <span className="text-xs text-ink-faint">to</span>
            <input
              type="number"
              className={`${inputCls} w-20`}
              value={vixTo}
              onChange={(e) => setVixTo(Number(e.target.value) || 0)}
            />
            <Button
              variant="secondary"
              className="h-8 px-3 text-xs"
              disabled
              title={RECALC_TOOLTIP}
            >
              Re-calculate
            </Button>
          </div>
          <p className="mt-1 text-xs text-ink-faint">{RECALC_TOOLTIP}</p>
        </div>
      </div>
    </Card>
  );
}

function SummaryStats({ s }: { s: BacktestSummary | null }) {
  const ddDuration =
    s && s.max_drawdown_start && s.max_drawdown_end
      ? `${s.max_drawdown_duration_days} days (${s.max_drawdown_start} → ${s.max_drawdown_end})`
      : s
        ? `${s.max_drawdown_duration_days} days`
        : "—";

  return (
    <div className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
      <div className="divide-y divide-rule">
        <StatRow label="Overall Profit" value={rupeeStr(s?.overall_profit)} colorClass={colorSign(s?.overall_profit ?? null)} />
        <StatRow label="No. of Trades" value={s ? String(s.total_trades) : "—"} />
        <StatRow label="Average Profit per Trade" value={rupeeStr(s?.avg_profit_per_trade)} colorClass={colorSign(s?.avg_profit_per_trade ?? null)} />
        <StatRow label="Win %" value={pctStr(s?.win_pct)} />
        <StatRow label="Loss %" value={pctStr(s?.loss_pct)} />
        <StatRow label="Average Profit on Winning Trades" value={rupeeStr(s?.avg_profit_on_winning)} colorClass="text-gain" />
      </div>
      <div className="divide-y divide-rule">
        <StatRow label="Average Loss on Losing Trades" value={rupeeStr(s?.avg_loss_on_losing)} colorClass="text-loss" />
        <StatRow label="Max Profit in Single Trade" value={rupeeStr(s?.max_profit_single_trade)} colorClass="text-gain" />
        <StatRow label="Max Loss in Single Trade" value={rupeeStr(s?.max_loss_single_trade)} colorClass="text-loss" />
        <StatRow label="Max Drawdown" value={rupeeStr(s?.max_drawdown != null ? -s.max_drawdown : null)} colorClass="text-loss" />
        <StatRow label="Duration of Max Drawdown" value={ddDuration} />
      </div>
      <div className="divide-y divide-rule">
        <StatRow label="Return / MaxDD" value={ratioStr(s?.return_over_max_dd)} />
        <StatRow label="Reward to Risk Ratio" value={ratioStr(s?.reward_to_risk_ratio)} />
        <StatRow label="Expectancy Ratio" value={rupeeStr(s?.expectancy_ratio)} colorClass={colorSign(s?.expectancy_ratio ?? null)} />
        <StatRow label="Max Win Streak (trades)" value={s ? String(s.max_win_streak) : "—"} />
        <StatRow label="Max Losing Streak (trades)" value={s ? String(s.max_losing_streak) : "—"} />
      </div>
    </div>
  );
}

function cellColor(v: number | null): string {
  if (v === null) return "text-ink-faint";
  if (v > 0) return "text-gain";
  if (v < 0) return "text-loss";
  return "text-ink";
}

// Pill-styled <select> — visible label never changes on selection (display
// only, no filtering logic wired up yet), matching the broker filter chips
// on the portfolio page. onInteract fires on every selection so the caller
// can surface feedback instead of the control silently doing nothing; the
// select itself resets to its placeholder so the pill's own label never
// lies about a filter being applied.
function PillSelect({
  label,
  options,
  isNew = false,
  onInteract,
}: {
  label: string;
  options: string[];
  isNew?: boolean;
  onInteract?: () => void;
}) {
  return (
    <div className="relative inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-rule px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-rule-strong hover:text-ink">
      <span>{label}</span>
      {isNew && <Badge tone="brand">NEW</Badge>}
      <span aria-hidden="true">▾</span>
      <select
        defaultValue=""
        aria-label={label}
        className="absolute inset-0 cursor-pointer opacity-0"
        onChange={(e) => {
          onInteract?.();
          e.currentTarget.value = "";
        }}
      >
        <option value="" disabled />
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

function FilterByRow() {
  const [msg, setMsg] = useState<string | null>(null);
  const handleInteract = () => setMsg(NOT_WIRED_MSG);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-xs font-medium text-ink-muted">Filter by</span>
      <PillSelect
        label="Weekdays"
        options={["All Days", "Weekdays", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
        onInteract={handleInteract}
      />
      <PillSelect
        label="DTE"
        options={["All", "DTE 0", "DTE 1", "DTE 2", "DTE 7"]}
        onInteract={handleInteract}
      />
      <PillSelect
        label="Budget Days"
        options={["Include", "Exclude"]}
        isNew
        onInteract={handleInteract}
      />
      <span className="text-xs text-ink-faint">
        {msg ?? "Filtering by day/DTE will apply once F&O historical data is integrated."}
      </span>
    </div>
  );
}

function YearlyReturnsTable({ rows }: { rows: YearlyReturn[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-right text-xs">
        <thead>
          <tr className="border-b border-rule text-ink-muted">
            <th className="px-2 py-2 text-left font-medium">Year</th>
            {MONTH_LABELS.map((m) => (
              <th key={m} className="px-2 py-2 font-medium">{m}</th>
            ))}
            <th className="px-2 py-2 font-medium">Total</th>
            <th className="px-2 py-2 font-medium">Max DD</th>
            <th className="px-2 py-2 font-medium">Days MDD</th>
            <th className="px-2 py-2 font-medium">R/MDD</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year} className="border-b border-rule last:border-0">
              <td className="px-2 py-2 text-left font-medium text-ink">{row.year}</td>
              {MONTH_KEYS.map((k) => {
                const v = row[k] as number | null;
                return (
                  <td key={k} className={`px-2 py-2 font-mono ${cellColor(v)}`}>
                    {v === null ? "—" : rupeeStr(v)}
                  </td>
                );
              })}
              <td className={`px-2 py-2 font-mono font-semibold ${cellColor(row.total)}`}>{rupeeStr(row.total)}</td>
              <td className="px-2 py-2 font-mono text-loss">{rupeeStr(row.max_drawdown != null ? -row.max_drawdown : null)}</td>
              <td className="px-2 py-2 font-mono text-ink">{row.days_for_mdd ?? "—"}</td>
              <td className="px-2 py-2 font-mono text-ink">{ratioStr(row.return_over_mdd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function downloadTradesCsv(trades: TradeRow[], strategyName: string) {
  const csv = [
    ["#", "Symbol", "Gain Type", "Entry Date", "Entry Price", "Exit Date", "Exit Price", "Holding Days", "Qty", "P&L"],
    ...trades.map((t) => [
      t.index, t.symbol, t.gain_type, t.entry_date, t.entry_price,
      t.exit_date, t.exit_price, t.holding_days, t.quantity, t.pnl,
    ]),
  ]
    .map((row) => row.join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `backtest-trades-${strategyName || "report"}-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function FullReportTable({ trades, strategyName }: { trades: TradeRow[]; strategyName: string }) {
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? trades : trades.slice(0, 10);

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SectionHeading>Full Report</SectionHeading>
          <span className="text-xs text-ink-faint">{trades.length} trades</span>
        </div>
        {trades.length > 0 && (
          <Button
            variant="secondary"
            className="h-8 px-3 text-xs"
            onClick={() => downloadTradesCsv(trades, strategyName)}
          >
            ↓ Download trades
          </Button>
        )}
      </div>
      <Card className="overflow-hidden p-0">
        <div className="max-h-[400px] overflow-y-auto">
          <table className="w-full min-w-[720px] text-right text-xs">
            <thead className="sticky top-0 bg-surface">
              <tr className="border-b border-rule text-ink-muted">
                <th className="px-3 py-2 text-left font-medium">#</th>
                <th className="px-3 py-2 text-left font-medium">Symbol</th>
                <th className="px-3 py-2 text-left font-medium">Gain Type</th>
                <th className="px-3 py-2 text-left font-medium">Entry Date</th>
                <th className="px-3 py-2 text-left font-medium">Exit Date</th>
                <th className="px-3 py-2 font-medium">Holding Days</th>
                <th className="px-3 py-2 font-medium">Qty</th>
                <th className="px-3 py-2 font-medium">Entry Price</th>
                <th className="px-3 py-2 font-medium">Exit Price</th>
                <th className="px-3 py-2 font-medium">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.index} className="border-b border-rule last:border-0">
                  <td className="px-3 py-2 text-left font-mono text-ink-muted">{t.index}</td>
                  <td className="px-3 py-2 text-left text-ink">{t.symbol}</td>
                  <td className="px-3 py-2 text-left text-ink-muted">{t.gain_type ?? "—"}</td>
                  <td className="px-3 py-2 text-left text-ink-muted">{t.entry_date ?? "—"}</td>
                  <td className="px-3 py-2 text-left text-ink-muted">{t.exit_date}</td>
                  <td className="px-3 py-2 font-mono text-ink">{t.holding_days}</td>
                  <td className="px-3 py-2 font-mono text-ink">{t.quantity}</td>
                  <td className="px-3 py-2 font-mono text-ink">{rupeeStr(t.entry_price)}</td>
                  <td className="px-3 py-2 font-mono text-ink">{rupeeStr(t.exit_price)}</td>
                  <td className={`px-3 py-2 font-mono font-medium ${colorSign(t.pnl)}`}>{rupeeStr(t.pnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      {trades.length > 10 && (
        <div className="mt-3">
          <Button variant="secondary" className="h-8 px-3 text-xs" onClick={() => setShowAll((v) => !v)}>
            {showAll ? "Show fewer" : `Show all ${trades.length} trades`}
          </Button>
        </div>
      )}
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function BacktestClient() {
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
        {/* LEFT — Strategy builder (40%), all sections stacked */}
        <div className="lg:col-span-2">
          <div className="space-y-8">
            {/* SECTION 1 — Instrument */}
            <section>
              <SectionHeading>Instrument settings</SectionHeading>
              <div className="mt-3 space-y-4">
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
              </div>
            </section>

            <hr className="border-rule" />

            {/* SECTION 2 — Entry settings */}
            <section>
              <SectionHeading>Entry settings</SectionHeading>
              <div className="mt-3 space-y-4">
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
              </div>
            </section>

            <hr className="border-rule" />

            {/* SECTION 3 — Legwise settings */}
            <section>
              <SectionHeading>Legwise settings</SectionHeading>
              <div className="mt-3 space-y-4">
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
              </div>
            </section>

            <hr className="border-rule" />

            {/* SECTION 4 — Leg Builder */}
            <section>
              <SectionHeading>Leg Builder</SectionHeading>
              <Card className="mt-3 p-5">
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
            </section>

            <hr className="border-rule" />

            {/* SECTION 5 — Overall strategy settings */}
            <section>
              <SectionHeading>Overall strategy settings</SectionHeading>
              <div className="mt-3 space-y-4">
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

                <h3 className="text-sm font-medium text-ink-muted">Trailing Options</h3>

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
              </div>
            </section>

            <hr className="border-rule" />

            {/* SECTION 6 — Duration */}
            <section>
              <SectionHeading>Enter the duration of your backtest</SectionHeading>
              <Card className="mt-3 p-5">
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
            </section>
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

        {/* RIGHT — Results panel (60%), sticky on desktop */}
        <div className="lg:col-span-3">
          <div className="lg:sticky lg:top-4">
            {running ? (
              <div className="space-y-4">
                <div className="h-6 w-48 animate-pulse rounded bg-rule" />
                <Card className="p-5">
                  <div className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-3">
                    {[0, 1, 2].map((col) => (
                      <div key={col} className="space-y-2">
                        {[0, 1, 2, 3, 4].map((i) => (
                          <div key={i} className="h-4 animate-pulse rounded bg-rule" />
                        ))}
                      </div>
                    ))}
                  </div>
                </Card>
                <Card className="p-5">
                  <div className="h-[320px] animate-pulse rounded bg-rule" />
                </Card>
                <Card className="p-5">
                  <div className="h-[200px] animate-pulse rounded bg-rule" />
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
              <div className="space-y-4">
                <Card className="border-estimate/30 bg-estimate-soft p-5">
                  <div className="flex items-start gap-3">
                    <span className="text-lg">⚠</span>
                    <div>
                      <p className="font-display text-base text-ink">
                        {result.strategy_type === "options"
                          ? "F&O Strategy Simulation Pending"
                          : "Not Enough Data"}
                      </p>
                      <p className="mt-1 text-sm text-ink-muted">{result.message}</p>
                      <p className="mt-2 text-xs text-ink-faint">
                        Your strategy has been saved. We&rsquo;ll notify you when F&amp;O
                        historical data is available.
                      </p>
                    </div>
                  </div>
                </Card>
                {/* Show the stat scaffold with "--" so the user sees what WILL populate */}
                <Card className="p-5">
                  <SummaryStats s={null} />
                </Card>
              </div>
            ) : (
              <div className="space-y-6">
                <ResultsHeader />

                <FilterRecalcRow />

                <Card className="p-5">
                  <SummaryStats s={result.summary ?? null} />
                </Card>

                <div>
                  <FilterByRow />
                  <div className="mt-4">
                    <SectionHeading>Year-wise Returns</SectionHeading>
                  </div>
                  <Card className="mt-3 p-5">
                    {result.yearly_returns && result.yearly_returns.length > 0 ? (
                      <YearlyReturnsTable rows={result.yearly_returns} />
                    ) : (
                      <p className="text-sm text-ink-faint">No yearly data.</p>
                    )}
                  </Card>
                </div>

                <div>
                  <SectionHeading>Equity Curve</SectionHeading>
                  <Card className="mt-3 p-5">
                    {result.equity_curve && result.equity_curve.length > 0 ? (
                      <EquityCurveChart data={result.equity_curve} />
                    ) : (
                      <p className="text-sm text-ink-faint">Not enough trade history to draw equity curve.</p>
                    )}
                  </Card>
                </div>

                {result.trades && result.trades.length > 0 && (
                  <FullReportTable trades={result.trades} strategyName={form.name} />
                )}
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
                          <td className={`px-4 py-2 font-mono ${colorSign(run.result_json?.summary?.overall_profit)}`}>
                            {rupeeStr(run.result_json?.summary?.overall_profit)}
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
    </div>
  );
}

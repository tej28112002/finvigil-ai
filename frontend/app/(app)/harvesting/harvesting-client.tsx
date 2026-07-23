"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetch } from "@/lib/api";

// ── types ────────────────────────────────────────────────────────────────────

interface FySummary {
  total_ltcg_booked: number;
  total_stcg_booked: number;
  total_ltcg_losses: number;
  total_stcg_losses: number;
  ltcg_exemption_remaining: number;
  net_ltcg: number;
  net_stcg: number;
  current_ltcg_tax: number;
  current_stcg_tax: number;
  total_tax_liability: number;
}

interface ApplicableLot {
  lot_id: string;
  symbol: string;
  instrument_type: string;
  buy_date: string;
  buy_price: number;
  quantity_remaining: number;
  holding_days: number;
  cost_basis_total: number;
  qualifies_for_ltcg: boolean;
}

interface Strategy {
  strategy_id: string;
  lot_id?: string;
  title: string;
  subtitle?: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  instructions: string[];
  legal_basis?: string;
  requires_live_price?: boolean;
  disclaimer?: string;
  fy_deadline?: string;
  days_until_fy_end?: number;
  tax_saving_estimate?: number;
  exemption_remaining?: number;
  applicable_lots?: ApplicableLot[];
  // holding_period_optimizer
  symbol?: string;
  buy_date?: string;
  buy_price?: number;
  quantity?: number;
  days_held?: number;
  days_to_ltcg?: number;
  ltcg_date?: string;
  cost_basis_total?: number;
  illustrative_tax_saving?: number;
  urgent?: boolean;
  // tax_loss_harvest
  current_tax_liability?: number;
  current_net_stcg?: number;
  current_net_ltcg?: number;
  loss_needed_to_zero_tax?: number;
  open_lots_count?: number;
  // fy_boundary_split
  exemption_this_fy?: number;
  exemption_next_fy?: number;
  total_tax_free_gains_possible?: number;
  // loss_carry_forward
  unabsorbed_loss?: number;
  future_tax_saving_estimate?: number;
  itr_deadline_reminder?: boolean;
  // setoff_optimizer
  optimal_tax?: number;
  set_off_breakdown?: {
    stcg_loss_against_stcg: number;
    stcg_loss_against_ltcg: number;
    ltcg_loss_against_ltcg: number;
  };
}

interface IntelligenceResponse {
  fy_summary: FySummary;
  strategies: Strategy[];
  total_strategies: number;
  potential_tax_saving: number;
  current_fy: string;
  assessment_year: string;
  rates: { stcg_rate_pct: number; ltcg_rate_pct: number; ltcg_exemption: number };
  disclaimer: string;
}

interface BrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}

const BROKER_LOGIN_URLS: Record<string, string> = {
  zerodha: "https://kite.zerodha.com",
  upstox: "https://pro.upstox.com",
  groww: "https://groww.in",
};

function brokerLabel(brokerName: string): string {
  return brokerName.charAt(0).toUpperCase() + brokerName.slice(1);
}

// ── helpers ──────────────────────────────────────────────────────────────────

function rupeeStr(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const sign = v < 0 ? "-" : "";
  return `${sign}₹${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function Skeleton({ className = "h-8 w-24" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-rule ${className}`} />;
}

function strategySaving(s: Strategy): number | null {
  return s.tax_saving_estimate ?? s.illustrative_tax_saving ?? s.future_tax_saving_estimate ?? null;
}

function PriorityBadge({ priority }: { priority: string }) {
  const tone = priority === "HIGH" ? "gain" : priority === "MEDIUM" ? "estimate" : "neutral";
  return <Badge tone={tone}>{priority}</Badge>;
}

// ── step-by-step guide modal ────────────────────────────────────────────────

function ImplementModal({
  strategy,
  brokers,
  onClose,
}: {
  strategy: Strategy;
  brokers: BrokerConnection[];
  onClose: () => void;
}) {
  const activeBroker = brokers.find((b) => b.status === "active");
  const brokerUrl = activeBroker ? BROKER_LOGIN_URLS[activeBroker.broker_name] : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="implement-modal-title"
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-md border border-rule bg-surface p-6 shadow-token-sm">
        <div className="flex items-start justify-between gap-3">
          <h2 id="implement-modal-title" className="font-display text-lg text-ink">
            How to Implement This Strategy
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 cursor-pointer rounded p-1 text-ink-faint hover:text-ink"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mt-3 text-sm text-ink-muted">
          Complete these steps in your broker account (Zerodha / Upstox / Groww):
        </p>

        <ul className="mt-3 space-y-2.5 text-sm text-ink">
          {strategy.instructions.map((step, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <input type="checkbox" disabled className="mt-1 shrink-0" aria-hidden="true" />
              <span>
                <span className="font-medium text-ink-muted">Step {i + 1}: </span>
                {step}
              </span>
            </li>
          ))}
        </ul>

        {strategy.legal_basis && (
          <p className="mt-4 text-xs text-ink-faint">
            <span className="font-medium text-ink-muted">Legal basis: </span>
            {strategy.legal_basis}
          </p>
        )}

        <div className="mt-4 flex items-start gap-2 rounded-md border border-brand/30 bg-surface px-3 py-2.5 text-xs text-ink-muted">
          <span aria-hidden="true">ℹ</span>
          <span>
            These are step-by-step instructions for you to execute in your
            broker account. FinVigil is a read-only platform and does not
            place trades on your behalf.
          </span>
        </div>

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          {activeBroker && brokerUrl ? (
            <Button
              variant="secondary"
              onClick={() => window.open(brokerUrl, "_blank", "noopener,noreferrer")}
            >
              Open {brokerLabel(activeBroker.broker_name)} →
            </Button>
          ) : (
            <Button variant="secondary" onClick={() => (window.location.href = "/brokers")}>
              Go to Brokers →
            </Button>
          )}
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}

// ── strategy-specific inline content ────────────────────────────────────────

function StrategySpecificContent({ strategy }: { strategy: Strategy }) {
  switch (strategy.strategy_id) {
    case "ltcg_exemption_harvest":
      if (!strategy.applicable_lots || strategy.applicable_lots.length === 0) return null;
      return (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-rule text-left text-ink-muted">
                <th className="px-2 py-1.5 font-medium">Symbol</th>
                <th className="px-2 py-1.5 font-medium">Buy Date</th>
                <th className="px-2 py-1.5 text-right font-medium">Buy Price</th>
                <th className="px-2 py-1.5 text-right font-medium">Qty</th>
                <th className="px-2 py-1.5 text-right font-medium">Days Held</th>
                <th className="px-2 py-1.5 text-right font-medium">Cost Basis</th>
                <th className="px-2 py-1.5 font-medium">LTCG Eligible</th>
              </tr>
            </thead>
            <tbody>
              {strategy.applicable_lots.map((lot) => (
                <tr key={lot.lot_id} className="border-b border-rule last:border-0">
                  <td className="px-2 py-1.5 text-ink">{lot.symbol}</td>
                  <td className="px-2 py-1.5 text-ink-muted">{lot.buy_date}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-ink">{rupeeStr(lot.buy_price)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-ink">{lot.quantity_remaining}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-ink">{lot.holding_days}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-ink">{rupeeStr(lot.cost_basis_total)}</td>
                  <td className="px-2 py-1.5">
                    <Badge tone="gain">Yes</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink-faint">Live price needed to show unrealized P&amp;L.</p>
        </div>
      );

    case "holding_period_optimizer":
      return (
        <div className="mt-4 rounded-md border border-rule bg-bg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-muted">Countdown</span>
            <span className="font-mono text-lg font-semibold text-ink">
              {strategy.days_to_ltcg} days remaining
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Qualifies for LTCG on <span className="font-medium text-ink">{strategy.ltcg_date}</span>
          </p>
          <p className="mt-2 text-xs text-ink-faint">
            At 20% STCG rate vs 12.5% LTCG rate — hold longer to save 7.5%.
          </p>
        </div>
      );

    case "fy_boundary_split": {
      const daysLeft = strategy.days_until_fy_end ?? 0;
      return (
        <div className="mt-4 rounded-md border border-rule bg-bg p-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="whitespace-nowrap rounded-full border border-rule px-2.5 py-1 text-ink-muted">
              This FY: {rupeeStr(strategy.exemption_this_fy ?? 0)} tax-free
            </span>
            <span className="h-px flex-1 bg-rule" aria-hidden="true" />
            <span className="whitespace-nowrap font-medium text-ink">March 31</span>
            <span className="h-px flex-1 bg-rule" aria-hidden="true" />
            <span className="whitespace-nowrap rounded-full border border-rule px-2.5 py-1 text-ink-muted">
              Next FY: {rupeeStr(strategy.exemption_next_fy ?? 0)} tax-free
            </span>
          </div>
          <p className="mt-2 text-center text-xs text-ink-faint">
            {daysLeft >= 0 ? `${daysLeft} days until March 31` : "This FY's deadline has passed"}
          </p>
        </div>
      );
    }

    case "tax_loss_harvest":
      return (
        <div className="mt-4 space-y-2 rounded-md border border-rule bg-bg p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Net STCG this FY</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.current_net_stcg ?? 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Net LTCG this FY</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.current_net_ltcg ?? 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Estimated tax liability</span>
            <span className="font-mono text-loss">{rupeeStr(strategy.current_tax_liability ?? 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Loss needed to zero out tax</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.loss_needed_to_zero_tax ?? 0)}</span>
          </div>
          <div className="pt-1">
            <a href="/brokers" className="text-xs font-medium text-brand hover:underline">
              Connect broker to see which holdings are at a loss →
            </a>
          </div>
        </div>
      );

    case "loss_carry_forward":
      return (
        <div className="mt-4 space-y-2 rounded-md border border-rule bg-bg p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Unabsorbed loss</span>
            <span className="font-mono text-loss">{rupeeStr(strategy.unabsorbed_loss ?? 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Future tax benefit</span>
            <span className="font-mono text-gain">{rupeeStr(strategy.future_tax_saving_estimate ?? 0)}</span>
          </div>
          {strategy.itr_deadline_reminder && <Badge tone="estimate">File ITR on time</Badge>}
        </div>
      );

    case "setoff_optimizer":
      if (!strategy.set_off_breakdown) return null;
      return (
        <div className="mt-4 space-y-1.5 rounded-md border border-rule bg-bg p-3 text-xs">
          <div className="flex justify-between">
            <span className="text-ink-muted">STCG loss → STCG gain</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.set_off_breakdown.stcg_loss_against_stcg)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">STCG loss → LTCG gain</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.set_off_breakdown.stcg_loss_against_ltcg)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">LTCG loss → LTCG gain</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.set_off_breakdown.ltcg_loss_against_ltcg)}</span>
          </div>
          <div className="flex justify-between border-t border-rule pt-1.5 font-medium">
            <span className="text-ink-muted">Optimal tax</span>
            <span className="font-mono text-ink">{rupeeStr(strategy.optimal_tax ?? 0)}</span>
          </div>
        </div>
      );

    default:
      return null;
  }
}

// ── strategy card ────────────────────────────────────────────────────────────

function StrategyCard({
  strategy,
  onImplement,
}: {
  strategy: Strategy;
  onImplement: (s: Strategy) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const saving = strategySaving(strategy);
  const isUrgent = strategy.urgent === true;

  return (
    <Card className={`p-5 ${isUrgent ? "border-loss/40" : ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <PriorityBadge priority={strategy.priority} />
        {isUrgent && <Badge tone="loss">URGENT</Badge>}
        <h3 className="font-display text-base text-ink">{strategy.title}</h3>
      </div>
      {strategy.subtitle && <p className="mt-1 text-sm text-ink-muted">{strategy.subtitle}</p>}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-ink-muted">
          {saving !== null ? (
            <>
              Potential saving:{" "}
              <span className="font-mono font-medium text-gain">{rupeeStr(saving)}</span>
            </>
          ) : (
            <span className="text-ink-faint">Saving depends on live price</span>
          )}
        </span>
        {strategy.legal_basis && (
          <span className="text-xs text-ink-faint">§ {strategy.legal_basis.split(",")[0]}</span>
        )}
      </div>

      <StrategySpecificContent strategy={strategy} />

      <div className="mt-4">
        <Button variant="ghost" className="h-8 px-2 text-xs" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "▲ Hide Instructions" : "▼ View Instructions"}
        </Button>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-rule pt-3">
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-ink">
            {strategy.instructions.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
          {strategy.legal_basis && <p className="mt-3 text-xs text-ink-faint">{strategy.legal_basis}</p>}
          {strategy.requires_live_price && (
            <div className="mt-2">
              <Badge tone="estimate">Requires live price data</Badge>
            </div>
          )}
          <div className="mt-3">
            <Button variant="secondary" className="h-8 px-3 text-xs" onClick={() => onImplement(strategy)}>
              📋 Step-by-Step Guide
            </Button>
            <p className="mt-1.5 text-xs text-ink-faint">
              Execute through your Zerodha / Upstox / Groww account
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── tax law reference ────────────────────────────────────────────────────────

function TaxLawReference({ data }: { data: IntelligenceResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="mt-8 p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between text-left"
      >
        <h2 className="font-display text-base text-ink">
          Indian Capital Gains Tax Reference ({data.assessment_year})
        </h2>
        <span className="text-ink-faint">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-5">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-rule text-left text-xs text-ink-muted">
                  <th className="px-2 py-2 font-medium">Type</th>
                  <th className="px-2 py-2 font-medium">Holding Period</th>
                  <th className="px-2 py-2 font-medium">Tax Rate</th>
                  <th className="px-2 py-2 font-medium">Annual Exemption</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-rule">
                  <td className="px-2 py-2 text-ink">LTCG (equity)</td>
                  <td className="px-2 py-2 text-ink-muted">&gt; 12 months</td>
                  <td className="px-2 py-2 font-mono text-ink">{data.rates.ltcg_rate_pct}%</td>
                  <td className="px-2 py-2 font-mono text-ink">{rupeeStr(data.rates.ltcg_exemption)}</td>
                </tr>
                <tr>
                  <td className="px-2 py-2 text-ink">STCG (equity)</td>
                  <td className="px-2 py-2 text-ink-muted">&le; 12 months</td>
                  <td className="px-2 py-2 font-mono text-ink">{data.rates.stcg_rate_pct}%</td>
                  <td className="px-2 py-2 text-ink-faint">None</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink">Set-off rules</h3>
            <ul className="mt-2 space-y-1 text-sm text-ink-muted">
              <li>STCG Loss → Can offset: STCG gains ✓, LTCG gains ✓</li>
              <li>LTCG Loss → Can offset: LTCG gains ✓, STCG gains ✗</li>
              <li>Carry forward: 8 years (file ITR on time)</li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink">Important dates</h3>
            <ul className="mt-2 space-y-1 text-sm text-ink-muted">
              <li>FY End: March 31, 2026</li>
              <li>ITR Filing Deadline: July 31, 2026</li>
            </ul>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function HarvestingClient() {
  const [data, setData] = useState<IntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalStrategy, setModalStrategy] = useState<Strategy | null>(null);
  const [brokers, setBrokers] = useState<BrokerConnection[]>([]);

  useEffect(() => {
    apiFetch<IntelligenceResponse>("/tax-harvest/intelligence")
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load tax-saving recommendations.")
      )
      .finally(() => setLoading(false));
    apiFetch<BrokerConnection[]>("/brokers/")
      .then(setBrokers)
      .catch(() => setBrokers([]));
  }, []);

  const fy = data?.fy_summary ?? null;
  const hasNoData =
    !loading &&
    data !== null &&
    data.total_strategies === 0 &&
    (fy?.total_ltcg_booked ?? 0) === 0 &&
    (fy?.total_stcg_booked ?? 0) === 0;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Tax Harvesting Intelligence</h1>
        <p className="mt-1 text-sm text-ink-muted">
          AI-powered strategies to legally minimize your capital gains tax. All
          strategies are based on Indian tax law.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
          {error}
        </div>
      )}

      {hasNoData ? (
        <EmptyState
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6" />
            </svg>
          }
          title="No trades to analyze yet."
          description="Sync your broker or import a tradebook to get personalized tax-saving recommendations."
          action={
            <Button onClick={() => (window.location.href = "/brokers")}>Go to Brokers →</Button>
          }
        />
      ) : (
        <>
          {/* SECTION 1 — FY tax dashboard */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card className="p-5">
              <MetricLabel>Current LTCG Booked</MetricLabel>
              <div className="mt-3">
                {loading ? (
                  <Skeleton />
                ) : (
                  <span className="font-mono text-2xl font-medium text-ink">
                    {rupeeStr(fy?.total_ltcg_booked ?? 0)}
                  </span>
                )}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Current STCG Booked</MetricLabel>
              <div className="mt-3">
                {loading ? (
                  <Skeleton />
                ) : (
                  <span className="font-mono text-2xl font-medium text-ink">
                    {rupeeStr(fy?.total_stcg_booked ?? 0)}
                  </span>
                )}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>LTCG Exemption Remaining</MetricLabel>
              <div className="mt-3">
                {loading ? (
                  <Skeleton />
                ) : (
                  <span
                    className={`font-mono text-2xl font-medium ${
                      (fy?.ltcg_exemption_remaining ?? 0) > 0 ? "text-gain" : "text-ink"
                    }`}
                  >
                    {rupeeStr(fy?.ltcg_exemption_remaining ?? 0)}
                  </span>
                )}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Estimated Tax Liability</MetricLabel>
              <div className="mt-3">
                {loading ? (
                  <Skeleton />
                ) : (
                  <span
                    className={`font-mono text-2xl font-medium ${
                      (fy?.total_tax_liability ?? 0) > 0 ? "text-loss" : "text-ink"
                    }`}
                  >
                    {rupeeStr(fy?.total_tax_liability ?? 0)}
                  </span>
                )}
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Potential Savings</MetricLabel>
              <div className="mt-3">
                {loading ? (
                  <Skeleton />
                ) : (
                  <span className="font-mono text-2xl font-medium text-gain">
                    {rupeeStr(data?.potential_tax_saving ?? 0)}
                  </span>
                )}
              </div>
            </Card>
          </div>

          {/* SECTION 2 — strategy cards */}
          <h2 className="mt-8 font-display text-lg text-ink">Your Tax-Saving Opportunities</h2>
          <div className="mt-4 space-y-4">
            {loading ? (
              [0, 1, 2].map((i) => (
                <Card key={i} className="p-5">
                  <Skeleton className="h-4 w-1/3" />
                  <div className="mt-3">
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                </Card>
              ))
            ) : data && data.strategies.length > 0 ? (
              data.strategies.map((s, i) => (
                <StrategyCard
                  key={`${s.strategy_id}-${s.lot_id ?? i}`}
                  strategy={s}
                  onImplement={setModalStrategy}
                />
              ))
            ) : (
              <Card className="p-5">
                <p className="text-sm text-ink-faint">
                  No active strategies right now — you&rsquo;re already tax-optimized for this FY.
                </p>
              </Card>
            )}
          </div>

          {/* SECTION 3 — tax law reference */}
          {data && <TaxLawReference data={data} />}
        </>
      )}

      <Card className="mt-6 p-4">
        <p className="text-xs text-ink-muted">
          Tax estimates are indicative only and do not include 4% cess,
          surcharge, or income from other sources. Consult your Chartered
          Accountant before executing any transaction. FinVigil does not
          provide investment or tax advice.
        </p>
      </Card>

      {modalStrategy && (
        <ImplementModal strategy={modalStrategy} brokers={brokers} onClose={() => setModalStrategy(null)} />
      )}
    </div>
  );
}

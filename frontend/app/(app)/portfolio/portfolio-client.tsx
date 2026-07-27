"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { BrokerChips } from "@/components/dashboard/broker-chips";
import { BrokerActionsBar } from "@/components/shared/broker-actions-bar";
import { PortfolioTable } from "@/app/(app)/portfolio/portfolio-table";
import { sumToPaise, parseDecimalToPaise } from "@/lib/format";
import { apiFetch } from "@/lib/api";

interface PortfolioItem {
  instrument_id: string; symbol: string; instrument_type: string;
  total_quantity: string; total_invested: string;
  average_buy_price: string; lot_count: number;
}
interface HoldingLot {
  id: string; instrument_id: string; quantity_bought: string;
  quantity_remaining: string; buy_price: string; buy_date: string; status: string;
}
interface BrokerConnection { id: string; broker_name: string; status: string; }
interface TopHolding { symbol: string; weight: number; instrument_type: string; }
interface XirrData {
  xirr: number | null;
  xirr_percent: number | null;
  alpha: number | null;
  alpha_percent: number | null;
  beta: number | null;
  benchmark: string;
  absolute_return_percent: number | null;
  cagr_percent: number | null;
  asset_allocation: Record<string, number> | null;
  top_holdings: TopHolding[] | null;
  volatility_percent: number | null;
  max_drawdown_percent: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  var_95_rupees: number | null;
}

const TYPE_LABELS: Record<string, string> = {
  equity: "Equity",
  fno: "F&O",
  mf: "Mutual Funds",
  crypto: "Crypto",
};

const ALLOCATION_BAR_COLORS = ["bg-brand", "bg-estimate", "bg-ink-muted", "bg-rule-strong"];

function pctColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-ink-faint";
  if (value > 0) return "text-gain";
  if (value < 0) return "text-loss";
  return "text-ink";
}

function pctStr(value: number | null | undefined, signed = true): string {
  if (value === null || value === undefined) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

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

/** A return-style metric: colored by sign (positive=gain, negative=loss). */
function ReturnCard({
  label,
  value,
  loading,
  subtitle,
}: {
  label: React.ReactNode;
  value: number | null;
  loading: boolean;
  subtitle: string;
}) {
  return (
    <Card className="p-5">
      <MetricLabel>{label}</MetricLabel>
      <div className="mt-3">
        {loading ? <MetricSkeleton /> : (
          <span className={`font-mono text-2xl font-medium ${pctColor(value)}`}>
            {pctStr(value)}
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-ink-faint">{loading ? "Loading…" : subtitle}</p>
    </Card>
  );
}

/** A risk/ratio-style metric: no sign coloring, always neutral ink, with an
 * explanatory tooltip since these aren't self-evidently "good" or "bad". */
function RatioCard({
  label,
  value,
  loading,
  tooltip,
  subtitle,
  format,
}: {
  label: string;
  value: number | null;
  loading: boolean;
  tooltip: string;
  subtitle: string;
  format: (v: number) => string;
}) {
  return (
    <Card className="p-5">
      <MetricLabel>
        {label}
        <InfoTip text={tooltip} />
      </MetricLabel>
      <div className="mt-3">
        {loading ? (
          <MetricSkeleton />
        ) : value !== null ? (
          <span className="font-mono text-2xl font-medium text-ink">{format(value)}</span>
        ) : (
          <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
        )}
      </div>
      <p className="mt-1 text-xs text-ink-faint">{loading ? "Loading…" : subtitle}</p>
    </Card>
  );
}

export function PortfolioClient({
  portfolio,
  holdings,
  brokers,
  totalEquityValue,
}: {
  portfolio: PortfolioItem[];
  holdings: HoldingLot[];
  brokers: BrokerConnection[];
  totalEquityValue: string | null;
}) {
  const router = useRouter();
  const [brokerFilter, setBrokerFilter] = useState<string | null>(null);
  const [xirrData, setXirrData] = useState<XirrData | null>(null);
  const [xirrLoading, setXirrLoading] = useState(true);

  useEffect(() => {
    apiFetch<XirrData>("/portfolio/xirr")
      .then((data) => setXirrData(data))
      .catch(() => setXirrData(null))
      .finally(() => setXirrLoading(false));
  }, []);

  const brokerConnected = brokers.some((b) => b.status === "active");

  const investedPaise = sumToPaise(portfolio.map((p) => p.total_invested));
  const currentPaise = totalEquityValue ? parseDecimalToPaise(totalEquityValue) : null;
  const pnlPaise = currentPaise !== null ? currentPaise - investedPaise : null;
  const pnlTone =
    pnlPaise === null ? ("plain" as const)
    : pnlPaise > 0n ? ("auto" as const)
    : pnlPaise < 0n ? ("auto" as const)
    : ("plain" as const);

  const xirrPct = xirrData?.xirr_percent ?? null;
  const alphaPct = xirrData?.alpha_percent ?? null;
  const betaVal = xirrData?.beta ?? null;
  const absoluteReturnPct = xirrData?.absolute_return_percent ?? null;
  const cagrPct = xirrData?.cagr_percent ?? null;
  const volatilityPct = xirrData?.volatility_percent ?? null;
  const maxDrawdownPct = xirrData?.max_drawdown_percent ?? null;
  const sharpe = xirrData?.sharpe_ratio ?? null;
  const sortino = xirrData?.sortino_ratio ?? null;
  const var95Paise =
    xirrData?.var_95_rupees != null ? BigInt(Math.round(xirrData.var_95_rupees * 100)) : null;

  const assetAllocation = xirrData?.asset_allocation ?? null;
  const allocationEntries = assetAllocation
    ? Object.entries(assetAllocation)
        .filter(([, pct]) => pct > 0)
        .sort((a, b) => b[1] - a[1])
    : [];
  const topHoldings = xirrData?.top_holdings ?? null;

  return (
    <>
      {/* A — Broker filter tabs */}
      <BrokerChips brokers={brokers} selected={brokerFilter} onSelect={setBrokerFilter} />

      {/* A2 — Connect/sync broker + upload tradebook */}
      <div className="mt-4">
        <BrokerActionsBar onUploadSuccess={() => router.refresh()} />
      </div>

      {/* SECTION 1 — Returns */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Invested Amount */}
        <Card className="p-5">
          <MetricLabel>Invested Amount</MetricLabel>
          <div className="mt-3">
            <Money value={investedPaise} size="lg" />
          </div>
        </Card>

        {/* Current Value */}
        <Card className="p-5">
          <MetricLabel>Current Value</MetricLabel>
          <div className="mt-3">
            {currentPaise !== null ? (
              <Money value={currentPaise} size="lg" />
            ) : (
              <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
            )}
          </div>
          {currentPaise === null && (
            <p className="mt-1 text-xs text-ink-faint">Sync a broker to see live value</p>
          )}
        </Card>

        {/* Profit / Loss */}
        <Card className="p-5">
          <MetricLabel>Profit / Loss</MetricLabel>
          <div className="mt-3">
            {pnlPaise !== null ? (
              <Money value={pnlPaise} size="lg" tone={pnlTone} signed />
            ) : (
              <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
            )}
          </div>
        </Card>

        {/* Absolute Return % */}
        <ReturnCard
          label="Absolute Return"
          value={absoluteReturnPct}
          loading={xirrLoading}
          subtitle={absoluteReturnPct !== null ? "Total return, unannualised" : "Not enough trade history"}
        />

        {/* CAGR */}
        <ReturnCard
          label="CAGR"
          value={cagrPct}
          loading={xirrLoading}
          subtitle={cagrPct !== null ? "Compound annual growth rate" : "Need 30+ days of history"}
        />
      </div>

      {/* SECTION 2 — Risk & Performance */}
      <h2 className="mt-8 font-display text-lg text-ink">Risk &amp; Performance</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* XIRR */}
        <ReturnCard
          label="XIRR"
          value={xirrPct}
          loading={xirrLoading}
          subtitle={xirrPct !== null ? "Annualised return (XIRR)" : "Not enough trade history"}
        />

        {/* Alpha */}
        <ReturnCard
          label={
            <>
              Alpha{" "}
              {xirrData && <span className="font-normal text-ink-faint">vs {xirrData.benchmark}</span>}
            </>
          }
          value={alphaPct}
          loading={xirrLoading}
          subtitle={alphaPct !== null ? `vs ${xirrData?.benchmark ?? "Nifty 50"}` : "Benchmark data unavailable"}
        />

        {/* Beta */}
        <RatioCard
          label="Beta (β)"
          value={betaVal}
          loading={xirrLoading}
          tooltip="How much your portfolio moves vs Nifty 50. 1.2 means 20% more volatile than the market."
          subtitle={betaVal !== null ? "vs Nifty 50 (β)" : "Need 30+ days of daily price data"}
          format={(v) => v.toFixed(2)}
        />

        {/* Volatility */}
        <RatioCard
          label="Volatility"
          value={volatilityPct}
          loading={xirrLoading}
          tooltip="Annualized standard deviation of daily returns. Higher means more price swings."
          subtitle={volatilityPct !== null ? "Annualised, of daily returns" : "Need 30+ days of daily price data"}
          format={(v) => `${v.toFixed(2)}%`}
        />

        {/* Sharpe Ratio */}
        <RatioCard
          label="Sharpe Ratio"
          value={sharpe}
          loading={xirrLoading}
          tooltip="Return earned per unit of total risk. Above 1 is good, above 2 is excellent."
          subtitle={sharpe !== null ? "Risk-adjusted return" : "Need XIRR and volatility"}
          format={(v) => v.toFixed(2)}
        />

        {/* Sortino Ratio */}
        <RatioCard
          label="Sortino Ratio"
          value={sortino}
          loading={xirrLoading}
          tooltip="Like Sharpe but only counts downside risk. More relevant for investors."
          subtitle={sortino !== null ? "Downside-adjusted return" : "Need 30+ days of daily price data"}
          format={(v) => v.toFixed(2)}
        />

        {/* Max Drawdown */}
        <RatioCard
          label="Max Drawdown"
          value={maxDrawdownPct}
          loading={xirrLoading}
          tooltip="Largest peak-to-trough loss you experienced. Lower is better."
          subtitle={maxDrawdownPct !== null ? "Worst peak-to-trough decline" : "Need 30+ days of daily price data"}
          format={(v) => `${v.toFixed(2)}%`}
        />

        {/* VaR 95% */}
        <Card className="p-5">
          <MetricLabel>
            VaR (95%)
            <InfoTip text="On 95% of trading days, your single-day loss will not exceed this amount." />
          </MetricLabel>
          <div className="mt-3">
            {xirrLoading ? (
              <MetricSkeleton />
            ) : var95Paise !== null ? (
              <Money value={var95Paise} size="lg" />
            ) : (
              <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
            )}
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {xirrLoading ? "Loading…" : var95Paise !== null ? "Worst-case single-day loss" : "Need 30+ days of daily price data"}
          </p>
        </Card>
      </div>

      {/* SECTION 3 — Composition */}
      <h2 className="mt-8 font-display text-lg text-ink">Composition</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Asset Allocation */}
        <Card className="p-5">
          <MetricLabel>Asset Allocation</MetricLabel>
          <div className="mt-4 space-y-3">
            {xirrLoading ? (
              [0, 1, 2].map((i) => (
                <div key={i} className="h-4 animate-pulse rounded bg-rule" />
              ))
            ) : allocationEntries.length > 0 ? (
              allocationEntries.map(([type, pct], i) => (
                <div key={type}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-ink-muted">{TYPE_LABELS[type] ?? type}</span>
                    <span className="font-mono text-ink">{pct.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-rule">
                    <div
                      className={`h-full rounded-full ${ALLOCATION_BAR_COLORS[i % ALLOCATION_BAR_COLORS.length]}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-ink-faint">No active holdings yet</p>
            )}
          </div>
        </Card>

        {/* Top Holdings */}
        <Card className="p-5">
          <MetricLabel>Top Holdings</MetricLabel>
          <div className="mt-4 space-y-3">
            {xirrLoading ? (
              [0, 1, 2].map((i) => (
                <div key={i} className="h-4 animate-pulse rounded bg-rule" />
              ))
            ) : topHoldings && topHoldings.length > 0 ? (
              topHoldings.map((h, i) => (
                <div key={h.symbol}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-ink-muted">
                      {i + 1}. {h.symbol}{" "}
                      <span className="text-ink-faint">({TYPE_LABELS[h.instrument_type] ?? h.instrument_type})</span>
                    </span>
                    <span className="font-mono text-ink">{h.weight.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-rule">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${Math.min(h.weight, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-ink-faint">No active holdings yet</p>
            )}
          </div>
        </Card>
      </div>

      {/* C — Holdings table */}
      {portfolio.length > 0 && (
        <div className="mt-6">
          <div className="mb-4 flex items-center gap-2">
            <Badge tone="estimate">Cost basis only</Badge>
            <p className="text-xs text-ink-faint">
              Live per-holding price is pending — figures show quantity and
              invested cost, not current market value.
            </p>
          </div>
          <PortfolioTable items={portfolio} lots={holdings} />
        </div>
      )}

      {/* D — Connect broker prompt, BOTTOM, only when no broker connected */}
      {!brokerConnected && (
        <Card className="mt-8 border-brand-soft bg-brand-soft/40 p-5">
          <p className="font-display text-lg text-ink">
            You are not connected to a broker
          </p>
          <p className="mt-1 text-sm text-ink-muted">
            Connect a broker to see live invested amount, current value, P&amp;L,
            XIRR, and holdings.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={() => (window.location.href = "/brokers")}>
              Connect your broker
            </Button>
            <Button
              variant="secondary"
              onClick={() => (window.location.href = "/brokers")}
            >
              Go to Brokers →
            </Button>
          </div>
        </Card>
      )}
    </>
  );
}

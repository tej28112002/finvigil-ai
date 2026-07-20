"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { BrokerChips } from "@/components/dashboard/broker-chips";
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
interface XirrData {
  xirr: number | null;
  xirr_percent: number | null;
  alpha: number | null;
  alpha_percent: number | null;
  beta: number | null;
  benchmark: string;
}

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
  const betaPct = xirrData?.beta ?? null;
  const loadingDash = xirrLoading ? "—" : undefined;

  return (
    <>
      {/* A — Broker filter tabs */}
      <BrokerChips brokers={brokers} selected={brokerFilter} onSelect={setBrokerFilter} />

      {/* B — Metrics row (6 cards, 3-per-row on desktop) */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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

        {/* XIRR */}
        <Card className="p-5">
          <MetricLabel>XIRR</MetricLabel>
          <div className="mt-3">
            <span className={`font-mono text-2xl font-medium ${pctColor(xirrPct)}`}>
              {loadingDash ?? pctStr(xirrPct)}
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {xirrLoading
              ? "Loading…"
              : xirrPct !== null
                ? "Annualised return (XIRR)"
                : "Not enough trade history"}
          </p>
        </Card>

        {/* Alpha */}
        <Card className="p-5">
          <MetricLabel>
            Alpha{" "}
            {xirrData && (
              <span className="font-normal text-ink-faint">
                vs {xirrData.benchmark}
              </span>
            )}
          </MetricLabel>
          <div className="mt-3">
            <span className={`font-mono text-2xl font-medium ${pctColor(alphaPct)}`}>
              {loadingDash ?? pctStr(alphaPct)}
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {xirrLoading
              ? "Loading…"
              : alphaPct !== null
                ? `vs ${xirrData?.benchmark ?? "Nifty 50"}`
                : "Benchmark data unavailable"}
          </p>
        </Card>

        {/* Beta */}
        <Card className="p-5">
          <MetricLabel>
            Beta (β){" "}
            <span
              title="Beta requires daily historical prices for each holding. This will be available once broker live price sync is connected."
              className="cursor-help text-ink-faint"
              aria-label="Info"
            >
              ⓘ
            </span>
          </MetricLabel>
          <div className="mt-3">
            {betaPct !== null ? (
              <span
                className="font-mono text-2xl font-medium text-ink"
                title="A Beta > 1 means your portfolio moves more than the market. Beta < 1 means it moves less."
              >
                {betaPct.toFixed(2)}
              </span>
            ) : (
              <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
            )}
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {betaPct !== null ? "vs Nifty 50 (β)" : "Need 30+ days of data"}
          </p>
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

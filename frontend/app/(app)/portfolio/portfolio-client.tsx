"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { BrokerChips } from "@/components/dashboard/broker-chips";
import { PortfolioTable } from "@/app/(app)/portfolio/portfolio-table";
import { sumToPaise, parseDecimalToPaise } from "@/lib/format";

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

  const brokerConnected = brokers.some((b) => b.status === "active");

  // Invested: sum of total_invested across all portfolio items
  const investedPaise = sumToPaise(portfolio.map((p) => p.total_invested));

  // Current value from dashboard total_equity_value
  const currentPaise =
    totalEquityValue ? parseDecimalToPaise(totalEquityValue) : null;

  // P&L: current − invested (null if current value unavailable)
  const pnlPaise = currentPaise !== null ? currentPaise - investedPaise : null;

  const pnlTone =
    pnlPaise === null
      ? ("plain" as const)
      : pnlPaise > 0n
        ? ("auto" as const)
        : pnlPaise < 0n
          ? ("auto" as const)
          : ("plain" as const);

  return (
    <>
      {/* A — Broker filter tabs */}
      <BrokerChips
        brokers={brokers}
        selected={brokerFilter}
        onSelect={setBrokerFilter}
      />

      {/* B — Metrics row (6 cards, 3-per-row on desktop) */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="p-5">
          <MetricLabel>Invested Amount</MetricLabel>
          <div className="mt-3">
            <Money value={investedPaise} size="lg" />
          </div>
        </Card>

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

        {/* Coming-soon metrics */}
        <Card className="p-5">
          <MetricLabel>
            XIRR{" "}
            <span
              title="XIRR will be available once live price feed is connected"
              className="cursor-help text-ink-faint"
              aria-label="Info"
            >
              ⓘ
            </span>
          </MetricLabel>
          <div className="mt-3">
            <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
          </div>
          <p className="mt-1 text-xs text-ink-faint">Coming soon</p>
        </Card>

        <Card className="p-5">
          <MetricLabel>Alpha</MetricLabel>
          <div className="mt-3">
            <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
          </div>
          <p className="mt-1 text-xs text-ink-faint">Coming soon</p>
        </Card>

        <Card className="p-5">
          <MetricLabel>Beta</MetricLabel>
          <div className="mt-3">
            <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
          </div>
          <p className="mt-1 text-xs text-ink-faint">Coming soon</p>
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

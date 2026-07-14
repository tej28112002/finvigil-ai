"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { BrokerChips } from "@/components/dashboard/broker-chips";
import { TaxMeterCard } from "@/components/dashboard/tax-meter-card";
import { TaxHealthScore } from "@/components/dashboard/tax-health-score";
import { OnboardingChecklist } from "@/components/dashboard/onboarding-checklist";
import { HoldingsTable } from "@/components/dashboard/holdings-table";
import { onboarding } from "@/lib/onboarding";

interface BrokerConnection { id: string; broker_name: string; status: string; }
interface PortfolioItem {
  instrument_id: string; symbol: string; instrument_type: string;
  total_quantity: string; average_buy_price: string; total_invested: string;
}
interface HoldingLot { instrument_id: string; broker_connection_id: string; }
interface FnoPosition { instrument_id: string; symbol: string; open_quantity: string; avg_buy_price: string; }
interface Step { label: string; done: boolean; href: string; cta: string; }
interface DashboardData { day_pnl: string; unrealized_pnl: string; }

export function DashboardClient({
  brokers, portfolio, holdings, fnoPositions,
  checklistSteps, dashboard, totalPaise,
  dayTone, unrealTone, portfolioEmpty,
  equityTax, cryptoNetTax, fnoPnl, assessmentYear,
  taxHealthScore, harvestCandidateCount,
}: {
  brokers: BrokerConnection[];
  portfolio: PortfolioItem[];
  holdings: HoldingLot[];
  fnoPositions: FnoPosition[];
  checklistSteps: Step[];
  dashboard: DashboardData;
  totalPaise: string;
  dayTone: -1 | 0 | 1;
  unrealTone: -1 | 0 | 1;
  portfolioEmpty: boolean;
  equityTax: string | null;
  cryptoNetTax: string | null;
  fnoPnl: string | null;
  assessmentYear: string;
  taxHealthScore: number;
  harvestCandidateCount: number;
}) {
  const [brokerFilter, setBrokerFilter] = useState<string | null>(null);

  // localStorage is unavailable during SSR, so these must default to false
  // on the first client render (matching the server) and only pick up the
  // real value after mount — reading them directly during render would
  // desync the client's first paint from the server HTML and trigger a
  // hydration mismatch on every element that follows the checklist.
  const [clientFlags, setClientFlags] = useState({
    visitedTax: false,
    exportedCA: false,
  });

  useEffect(() => {
    setClientFlags({
      visitedTax: onboarding.hasVisitedTax(),
      exportedCA: onboarding.hasExportedCA(),
    });
  }, []);

  const steps = checklistSteps.map((s) => {
    if (s.href === "/tax") return { ...s, done: clientFlags.visitedTax };
    if (s.href === "/export") return { ...s, done: clientFlags.exportedCA };
    return s;
  });

  return (
    <>
      <BrokerChips brokers={brokers} selected={brokerFilter} onSelect={setBrokerFilter} />

      {portfolioEmpty && (
        <Card className="border-brand-soft bg-brand-soft/40 p-5">
          <p className="font-display text-lg text-ink">Connect your broker</p>
          <p className="mt-1 text-sm text-ink-muted">
            Link Zerodha or import a tradebook to see your consolidated
            portfolio and tax picture here.
          </p>
          <Button onClick={() => (window.location.href = "/brokers")} className="mt-3">
            Go to Brokers
          </Button>
        </Card>
      )}

      {/* Row 1 — hero metrics. Total portfolio value spans 2 of 4 columns at
          lg: it's the biggest number on the page (size="xl" statement
          numerals) and was overflowing its card when it had to share an
          equal 1/5 slot with four smaller-font cards in a single row. Day
          P&L / Unrealized P&L keep the same 1-column width they always had
          (this grid is still 4 columns at lg, same as before Tax Health
          Score existed) — only Total Portfolio Value got wider, nothing
          else got narrower. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5 lg:col-span-2">
          <MetricLabel>Total portfolio value</MetricLabel>
          <div className="mt-3">
            <Money value={BigInt(totalPaise)} size="xl" />
          </div>
          <p className="mt-2 text-xs text-ink-faint">Across all connected brokers</p>
        </Card>

        <Card className="p-5">
          <MetricLabel>Day P&amp;L</MetricLabel>
          <div className="mt-3">
            <Money value={dashboard.day_pnl} size="lg" tone="auto" signed />
          </div>
          {dayTone === 0 && (
            <p className="mt-2 text-xs text-ink-faint">Live prices resume on next broker sync</p>
          )}
        </Card>

        <Card className="p-5">
          <MetricLabel>Unrealized P&amp;L</MetricLabel>
          <div className="mt-3">
            <Money value={dashboard.unrealized_pnl} size="lg" tone="auto" signed />
          </div>
          {unrealTone === 0 && (
            <p className="mt-2 text-xs text-ink-faint">Based on last available prices</p>
          )}
        </Card>
      </div>

      {/* Row 2 — tax metrics. A separate, wider 2-column row (not squeezed
          into row 1) so both cards get a full half-width slot instead of a
          cramped 1/5 or 1/6. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TaxMeterCard
          equityTax={equityTax}
          cryptoNetTax={cryptoNetTax}
          fnoPnl={fnoPnl}
          assessmentYear={assessmentYear}
        />

        <TaxHealthScore score={taxHealthScore} candidateCount={harvestCandidateCount} />
      </div>

      <OnboardingChecklist steps={steps} />

      <div>
        <h2 className="font-display mb-3 text-lg text-ink">Holdings</h2>
        <HoldingsTable
          portfolio={portfolio}
          holdings={holdings}
          brokers={brokers}
          fnoPositions={fnoPositions}
          brokerFilter={brokerFilter}
        />
      </div>
    </>
  );
}

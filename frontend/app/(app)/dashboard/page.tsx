import { Suspense } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { BrokerChips } from "@/components/dashboard/broker-chips";
import { TaxMeterCard } from "@/components/dashboard/tax-meter-card";
import { OnboardingChecklist } from "@/components/dashboard/onboarding-checklist";
import { HoldingsTable } from "@/components/dashboard/holdings-table";
import { DEFAULT_AY, getCurrentAY } from "@/lib/ay";
import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { sumToPaise, decimalSign, parseDecimalToPaise } from "@/lib/format";
import { computeTaxHealthScore } from "@/lib/harvest-score";
import { DashboardClient } from "@/app/(app)/dashboard/dashboard-client";

interface DashboardData {
  total_equity_value: string;
  total_crypto_value: string;
  day_pnl: string;
  unrealized_pnl: string;
}
interface BrokerConnection { id: string; broker_name: string; status: string; }
interface PortfolioItem {
  instrument_id: string; symbol: string; instrument_type: string;
  total_quantity: string; average_buy_price: string; total_invested: string;
}
interface HoldingLot { instrument_id: string; broker_connection_id: string; }
interface FnoPosition { instrument_id: string; symbol: string; open_quantity: string; avg_buy_price: string; }
interface EquityTax { total_tax_liability: string; }
interface CryptoTax { net_tax_payable: string; }
interface FnoPnl { total_pnl: string; }
interface HarvestSummary { total_harvestable_loss: string; candidate_count: number; }

export default async function DashboardPage() {
  // All data fetched server-side in parallel — no useEffect, no client waterfall.
  // Session is read ONCE and the token passed to every call below; reading it
  // per-call (the old pattern) measurably multiplied load time (see api-server.ts).
  const token = await getServerToken();
  const harvestAy = getCurrentAY(); // Phase 7 — harvesting is "right now", not DEFAULT_AY (see lib/ay.ts)
  const [dashboard, brokers, portfolio, holdings, fnoPositions, trades, cryptoTax, fnoPnlAy, equityTax, harvestSummary] =
    await Promise.all([
      apiFetchServer<DashboardData>("/dashboard/", token),
      apiFetchServer<BrokerConnection[]>("/brokers/", token),
      apiFetchServer<PortfolioItem[]>("/portfolio/", token),
      apiFetchServer<HoldingLot[]>("/holdings/", token),
      apiFetchServer<FnoPosition[]>("/fno/positions", token),
      apiFetchServer<{ id: string }[]>("/trades/", token),
      apiFetchServer<CryptoTax>(`/crypto/tax/${DEFAULT_AY}`, token),
      apiFetchServer<FnoPnl>(`/fno/pnl/${DEFAULT_AY}`, token),
      apiFetchServer<EquityTax>(`/tax/summary/${DEFAULT_AY}`, token),
      apiFetchServer<HarvestSummary>(`/harvesting/summary/${harvestAy}`, token),
    ]);

  if (!dashboard) {
    return (
      <Card className="mx-auto max-w-md p-8 text-center">
        <p className="text-sm font-medium text-ink">Could not load dashboard</p>
        <p className="mt-1 text-sm text-ink-muted">Check that the backend is running.</p>
      </Card>
    );
  }

  const brokerList = brokers ?? [];
  const portfolioList = portfolio ?? [];
  const holdingList = holdings ?? [];
  const fnoList = fnoPositions ?? [];
  const tradeCount = trades?.length ?? 0;

  const totalPaise = sumToPaise([
    dashboard.total_equity_value,
    dashboard.total_crypto_value,
  ]);
  const dayTone = decimalSign(dashboard.day_pnl);
  const unrealTone = decimalSign(dashboard.unrealized_pnl);
  const brokerConnected = brokerList.some((b) => b.status === "active");
  const portfolioEmpty = portfolioList.length === 0 && fnoList.length === 0;

  const checklistSteps = [
    { label: "Broker connected", done: brokerConnected, href: "/brokers", cta: "Connect a broker" },
    { label: "Trade history imported", done: tradeCount > 0, href: "/brokers", cta: "Sync or import trades" },
    { label: "Tax picture viewed", done: false, href: "/tax", cta: "View your tax summary" },
    { label: "CA report exported", done: false, href: "/export", cta: "Generate a CA report" },
  ];

  const candidateCount = harvestSummary?.candidate_count ?? 0;
  const harvestableLossPaise = harvestSummary
    ? -parseDecimalToPaise(harvestSummary.total_harvestable_loss) // stored signed-negative; score wants a magnitude
    : 0n;
  const totalOpenPositions = portfolioList.length + fnoList.length;
  const taxHealthScore = computeTaxHealthScore({
    candidateCount,
    totalOpenPositions,
    harvestableLossPaise,
    totalPortfolioPaise: totalPaise,
  });

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      {/* Broker chips + onboarding flags are client-only (localStorage + interactivity) */}
      <DashboardClient
        brokers={brokerList}
        portfolio={portfolioList}
        holdings={holdingList}
        fnoPositions={fnoList}
        checklistSteps={checklistSteps}
        dashboard={dashboard}
        totalPaise={String(totalPaise)}
        dayTone={dayTone}
        unrealTone={unrealTone}
        portfolioEmpty={portfolioEmpty}
        equityTax={equityTax?.total_tax_liability ?? null}
        cryptoNetTax={cryptoTax?.net_tax_payable ?? null}
        fnoPnl={fnoPnlAy?.total_pnl ?? null}
        assessmentYear={DEFAULT_AY}
        taxHealthScore={taxHealthScore}
        harvestCandidateCount={candidateCount}
      />

      <div className="flex items-center gap-2">
        <Badge tone="estimate">Estimates</Badge>
        <p className="text-xs text-ink-faint">
          Valuations use the latest synced prices and fall back to cost basis
          when a live price isn&apos;t available.
        </p>
      </div>
    </div>
  );
}

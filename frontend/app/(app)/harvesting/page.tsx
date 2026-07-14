import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { getCurrentAY } from "@/lib/ay";

interface HarvestCandidate {
  lot_id: string;
  instrument_id: string;
  symbol: string;
  quantity: string;
  buy_price: string;
  buy_date: string;
  current_value: string;
  is_price_estimate: boolean;
  unrealized_loss: string;
  holding_period_days: number;
  gain_type: string;
  estimated_tax_saving: string;
}
interface HarvestSummary {
  assessment_year: string;
  total_harvestable_loss: string;
  total_estimated_tax_saving: string;
  candidate_count: number;
  days_until_march_31: number;
  disclaimer: string;
}

export default async function HarvestingPage() {
  // Phase 7 — this feature is inherently "right now": harvest a loss before
  // THIS year's March 31. Uses the real current AY, not the app's stale
  // DEFAULT_AY constant (see lib/ay.ts's getCurrentAY doc comment — the
  // fixed AY_OPTIONS list only covers already-closed years).
  const ay = getCurrentAY();
  const token = await getServerToken();

  const [summary, candidates] = await Promise.all([
    apiFetchServer<HarvestSummary>(`/harvesting/summary/${ay}`, token),
    apiFetchServer<HarvestCandidate[]>(`/harvesting/candidates/${ay}`, token),
  ]);

  const list = candidates ?? [];

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Tax-loss harvesting</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Assessment year {ay} — positions sitting at a loss right now.
        </p>
      </div>

      {/* Summary banner */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <MetricLabel>Harvestable loss</MetricLabel>
          <div className="mt-3">
            <Money value={summary?.total_harvestable_loss ?? "0"} size="lg" tone="auto" signed />
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {summary?.candidate_count ?? 0} position{summary?.candidate_count === 1 ? "" : "s"} at a loss
          </p>
        </Card>
        <Card className="p-5">
          <MetricLabel>Estimated tax saving</MetricLabel>
          <div className="mt-3">
            <Money value={summary?.total_estimated_tax_saving ?? "0"} size="lg" />
          </div>
          <p className="mt-1 text-xs text-ink-faint">If harvested and offset this AY</p>
        </Card>
        <Card className="p-5">
          <MetricLabel>Days left this FY</MetricLabel>
          <div className="mt-3 font-mono text-2xl font-medium text-ink">
            {summary?.days_until_march_31 ?? 0}
          </div>
          <p className="mt-1 text-xs text-ink-faint">Until March 31</p>
        </Card>
      </div>

      {/* Candidates table */}
      <div className="mt-6">
        {list.length === 0 ? (
          <EmptyState
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
                <path d="M2 21c0-3 1.85-5.36 5.08-6" />
              </svg>
            }
            title="No harvest candidates right now"
            description="None of your open positions are currently showing an unrealized loss based on the latest available price data. Check back after your next broker sync, or once the market moves."
          />
        ) : (
          <Table>
            <THead>
              <Th>Symbol</Th>
              <Th>Type</Th>
              <Th align="right">Qty</Th>
              <Th align="right">Buy price</Th>
              <Th align="right">Current value</Th>
              <Th align="right">Unrealized loss</Th>
              <Th align="right">Est. tax saving</Th>
            </THead>
            <tbody>
              {list.map((c) => (
                <Tr key={c.lot_id}>
                  <Td className="font-medium">{c.symbol}</Td>
                  <Td>
                    <Badge tone={c.gain_type === "LTCG" ? "brand" : "neutral"}>{c.gain_type}</Badge>
                  </Td>
                  <Td align="right" className="font-mono">{c.quantity}</Td>
                  <Td align="right"><Money value={c.buy_price} size="sm" /></Td>
                  <Td align="right"><Money value={c.current_value} size="sm" /></Td>
                  <Td align="right"><Money value={c.unrealized_loss} size="sm" tone="auto" signed /></Td>
                  <Td align="right"><Money value={c.estimated_tax_saving} size="sm" /></Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Card className="mt-4 p-4">
        <p className="flex items-start gap-2 text-xs text-ink-muted">
          <Badge tone="estimate">Not financial advice</Badge>
          <span>{summary?.disclaimer ?? "Selling these positions before March 31 may reduce your tax liability. This is not financial advice — consult your CA before acting."}</span>
        </p>
      </Card>
    </div>
  );
}

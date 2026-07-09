import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetchServer } from "@/lib/api-server";
import { FnoActions } from "@/app/(app)/fno/fno-actions";

interface FnoOpenPosition { instrument_id: string; symbol: string; open_quantity: string; avg_buy_price: string; }
interface FnoEntry {
  id: string; symbol: string; quantity: string;
  buy_price: string; sell_price: string;
  buy_time: string | null; sell_time: string;
  profit_loss: string; is_intraday: boolean;
}
interface FnoPnlSummary {
  total_pnl: string; intraday_pnl: string; positional_pnl: string;
  realized_entry_count: number;
  open_positions: FnoOpenPosition[];
  entries: FnoEntry[];
  disclaimer: string;
}

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default async function FnoPage() {
  const data = await apiFetchServer<FnoPnlSummary>("/fno/pnl/");

  const hasData = data && (data.realized_entry_count > 0 || data.open_positions.length > 0);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex items-center justify-end">
        <FnoActions />
      </div>

      {!hasData ? (
        <EmptyState
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 3v18h18" /><path d="m7 14 4-4 3 3 5-6" />
            </svg>
          }
          title="No F&O activity yet"
          description="Once F&O trades are synced or imported, recalculate to see matched P&L here."
          action={<FnoActions />}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-5">
              <MetricLabel>Total P&amp;L</MetricLabel>
              <div className="mt-3"><Money value={data!.total_pnl} size="lg" tone="auto" signed /></div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Intraday (speculative)</MetricLabel>
              <div className="mt-3"><Money value={data!.intraday_pnl} size="lg" tone="auto" signed /></div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Positional (non-speculative)</MetricLabel>
              <div className="mt-3"><Money value={data!.positional_pnl} size="lg" tone="auto" signed /></div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Open positions</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-ink">{data!.open_positions.length}</div>
            </Card>
          </div>

          {data!.open_positions.length > 0 && (
            <div className="mt-6">
              <h2 className="font-display mb-2 text-lg text-ink">Open positions</h2>
              <Table>
                <THead><Th>Symbol</Th><Th align="right">Qty</Th><Th align="right">Avg buy</Th></THead>
                <tbody>
                  {data!.open_positions.map((p) => (
                    <Tr key={p.instrument_id}>
                      <Td className="font-medium">{p.symbol}</Td>
                      <Td align="right" className="font-mono">{p.open_quantity}</Td>
                      <Td align="right"><Money value={p.avg_buy_price} size="sm" /></Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}

          {data!.entries.length > 0 && (
            <div className="mt-6">
              <h2 className="font-display mb-2 text-lg text-ink">Realized entries</h2>
              <Table>
                <THead>
                  <Th>Symbol</Th><Th align="right">Qty</Th>
                  <Th align="right">Buy</Th><Th align="right">Sell</Th>
                  <Th>Sell time</Th><Th align="right">P&amp;L</Th><Th>Type</Th>
                </THead>
                <tbody>
                  {data!.entries.map((e) => (
                    <Tr key={e.id}>
                      <Td className="font-medium">{e.symbol}</Td>
                      <Td align="right" className="font-mono">{e.quantity}</Td>
                      <Td align="right"><Money value={e.buy_price} size="sm" /></Td>
                      <Td align="right"><Money value={e.sell_price} size="sm" /></Td>
                      <Td className="text-ink-muted">{fmtTime(e.sell_time)}</Td>
                      <Td align="right"><Money value={e.profit_loss} size="sm" tone="auto" signed /></Td>
                      <Td>
                        <Badge tone={e.is_intraday ? "brand" : "neutral"}>
                          {e.is_intraday ? "Intraday" : "Positional"}
                        </Badge>
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}
        </>
      )}

      {data && (
        <Card className="mt-6 p-4">
          <p className="flex items-start gap-2 text-xs text-ink-muted">
            <Badge tone="estimate">Estimate</Badge>
            <span>{data.disclaimer}</span>
          </p>
        </Card>
      )}
    </div>
  );
}

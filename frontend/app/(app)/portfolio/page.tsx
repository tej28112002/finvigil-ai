import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { PortfolioTable } from "@/app/(app)/portfolio/portfolio-table";

interface PortfolioItem {
  instrument_id: string; symbol: string; name: string;
  instrument_type: string; isin: string | null;
  total_quantity: string; total_invested: string;
  average_buy_price: string; lot_count: number; earliest_buy_date: string;
}
interface HoldingLot {
  id: string; instrument_id: string; quantity_bought: string;
  quantity_remaining: string; buy_price: string; buy_date: string; status: string;
}

export default async function PortfolioPage() {
  const token = await getServerToken();
  const [portfolio, holdings] = await Promise.all([
    apiFetchServer<PortfolioItem[]>("/portfolio/", token),
    apiFetchServer<HoldingLot[]>("/holdings/", token),
  ]);

  const items = portfolio ?? [];

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-5xl">
        <EmptyState
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 2 2 7l10 5 10-5-10-5Z" />
              <path d="m2 17 10 5 10-5" />
            </svg>
          }
          title="No holdings yet"
          description="Connect a broker or import a tradebook to see your open positions here."
          action={<a href="/brokers" className="inline-flex h-9 items-center rounded-md bg-brand px-4 text-sm font-medium text-brand-fg">Connect a broker</a>}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4 flex items-center gap-2">
        <Badge tone="estimate">Cost basis only</Badge>
        <p className="text-xs text-ink-faint">
          Live per-holding price is pending — figures below are quantity and
          invested cost, not current market value.
        </p>
      </div>
      <PortfolioTable items={items} lots={holdings ?? []} />
    </div>
  );
}

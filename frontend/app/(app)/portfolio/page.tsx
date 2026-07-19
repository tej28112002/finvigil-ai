import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { PortfolioClient } from "@/app/(app)/portfolio/portfolio-client";

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
interface BrokerConnection { id: string; broker_name: string; status: string; }
interface DashboardData { total_equity_value: string; total_crypto_value: string; }

export default async function PortfolioPage() {
  const token = await getServerToken();
  const [portfolio, holdings, brokers, dashboard] = await Promise.all([
    apiFetchServer<PortfolioItem[]>("/portfolio/", token),
    apiFetchServer<HoldingLot[]>("/holdings/", token),
    apiFetchServer<BrokerConnection[]>("/brokers/", token),
    apiFetchServer<DashboardData>("/dashboard/", token),
  ]);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="font-display mb-6 text-2xl font-bold text-ink">
        Cross Broker Portfolio
      </h1>
      <PortfolioClient
        portfolio={portfolio ?? []}
        holdings={holdings ?? []}
        brokers={brokers ?? []}
        totalEquityValue={dashboard?.total_equity_value ?? null}
      />
    </div>
  );
}

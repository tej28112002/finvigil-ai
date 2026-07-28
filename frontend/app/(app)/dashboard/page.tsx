import { createClient } from "@/lib/supabase/server";
import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { DashboardHome } from "@/app/(app)/dashboard/dashboard-client";

interface PortfolioItem {
  instrument_id: string;
  total_invested: string;
}
interface BrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}
interface DashboardData {
  total_equity_value: string;
  total_crypto_value: string;
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const fullName = (user?.user_metadata?.full_name as string | undefined) ?? "";
  const email = user?.email ?? "";

  let firstName = "";
  if (fullName.trim()) {
    firstName = fullName.trim().split(/\s+/)[0] ?? "";
  } else if (email) {
    firstName = email.split("@")[0] ?? "";
  }
  if (firstName) {
    firstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);
  }

  const token = await getServerToken();
  const [portfolio, brokers, dashboard] = await Promise.all([
    apiFetchServer<PortfolioItem[]>("/portfolio/", token),
    apiFetchServer<BrokerConnection[]>("/brokers/", token),
    apiFetchServer<DashboardData>("/dashboard/", token),
  ]);

  const hasData = (portfolio?.length ?? 0) > 0;

  return (
    <DashboardHome
      userId={user?.id ?? ""}
      firstName={firstName}
      hasData={hasData}
      portfolio={portfolio ?? []}
      brokers={brokers ?? []}
      totalEquityValue={dashboard?.total_equity_value ?? null}
    />
  );
}

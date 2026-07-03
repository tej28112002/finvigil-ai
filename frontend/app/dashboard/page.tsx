"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

interface DashboardData {
  total_equity_value: string;
  total_crypto_value: string;
  day_pnl: string;
  unrealized_pnl: string;
}

function formatInr(value: string): string {
  const num = Number(value);
  return num.toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push("/login");
        return;
      }

      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/dashboard/`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (!res.ok) {
          throw new Error(`Backend returned ${res.status}`);
        }

        const json: DashboardData = await res.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [router]);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-500">Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-red-600">Error: {error}</p>
      </div>
    );
  }

  const totalPortfolioValue =
    Number(data!.total_equity_value) + Number(data!.total_crypto_value);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-900"
          >
            Log out
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">Total Portfolio Value</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">
              {formatInr(totalPortfolioValue.toString())}
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">Day P&amp;L</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">
              {formatInr(data!.day_pnl)}
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">Unrealized P&amp;L</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">
              {formatInr(data!.unrealized_pnl)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

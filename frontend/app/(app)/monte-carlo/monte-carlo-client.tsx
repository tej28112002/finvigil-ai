"use client";

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { apiFetch, ApiError } from "@/lib/api";

// ── types ────────────────────────────────────────────────────────────────────

interface PercentileBand {
  year: number;
  p5: string;
  p25: string;
  p50: string;
  p75: string;
  p95: string;
}

interface FinalDistribution {
  p5: string;
  p25: string;
  p50: string;
  p75: string;
  p95: string;
  mean: string;
}

interface ParametersUsed {
  starting_value: string;
  horizon_years: number;
  annual_drift: string;
  annual_volatility: string;
  num_paths: number;
}

interface MonteCarloResultData {
  bands: PercentileBand[];
  final_distribution: FinalDistribution;
  parameters_used: ParametersUsed;
  disclaimer: string;
}

interface MonteCarloRunResponse {
  id: string;
  result_data: MonteCarloResultData | null;
  status: string;
}

// ── helpers ──────────────────────────────────────────────────────────────────

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

function InputRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
      <label className="w-44 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
        {label}
      </label>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function formatChartINR(val: number) {
  if (val >= 1_00_00_000) return `₹${(val / 1_00_00_000).toFixed(1)}Cr`;
  if (val >= 1_00_000) return `₹${(val / 1_00_000).toFixed(1)}L`;
  if (val >= 1_000) return `₹${(val / 1_000).toFixed(0)}K`;
  return `₹${val.toFixed(0)}`;
}

// ── main component ────────────────────────────────────────────────────────────

export function MonteCarloClient() {
  const [startingValue, setStartingValue] = useState("500000");
  const [horizonYears, setHorizonYears] = useState(10);
  const [cpiRate, setCpiRate] = useState("5");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MonteCarloRunResponse | null>(null);

  async function handleRun() {
    setError(null);
    setResult(null);

    const sv = parseFloat(startingValue);
    if (!sv || sv <= 0) {
      setError("Starting value must be a positive number.");
      return;
    }
    const cpi = parseFloat(cpiRate);
    if (isNaN(cpi) || cpi < 0 || cpi > 50) {
      setError("CPI rate must be between 0% and 50%.");
      return;
    }

    setRunning(true);
    try {
      const run = await apiFetch<MonteCarloRunResponse>("/monte-carlo/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          starting_value: sv.toString(),
          horizon_years: horizonYears,
          cpi_rate: (cpi / 100).toString(),
          num_paths: 1000,
        }),
      });
      setResult(run);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Monte Carlo simulations require a Pro or Premium subscription. Please upgrade to access this feature.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      setRunning(false);
    }
  }

  const data = result?.result_data;

  // Transform bands for Recharts
  const chartData = data?.bands.map((b) => ({
    year: `Year ${b.year}`,
    p5: parseFloat(b.p5),
    p25: parseFloat(b.p25),
    p50: parseFloat(b.p50),
    p75: parseFloat(b.p75),
    p95: parseFloat(b.p95),
  }));

  return (
    <div className="mx-auto max-w-5xl">
      {/* Page header */}
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Monte Carlo Simulation</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Project 1,000 possible growth paths for a portfolio value using Geometric Brownian Motion.
        </p>
      </div>

      {/* ── Configuration card ── */}
      <Card className="p-5">
        <h2 className="mb-4 font-display text-base text-ink">Parameters</h2>

        <div className="space-y-4">
          <InputRow label="Starting value (₹)">
            <input
              type="number"
              className={inputCls}
              placeholder="e.g. 500000"
              min="1"
              step="1000"
              value={startingValue}
              onChange={(e) => setStartingValue(e.target.value)}
            />
          </InputRow>

          <InputRow label="Horizon (years)">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="1"
                max="30"
                value={horizonYears}
                onChange={(e) => setHorizonYears(parseInt(e.target.value))}
                className="flex-1 accent-brand"
              />
              <span className="w-10 text-right font-mono text-sm text-ink">
                {horizonYears}
              </span>
            </div>
          </InputRow>

          <InputRow label="Expected drift / CPI (%)">
            <input
              type="number"
              className={inputCls}
              placeholder="5"
              min="0"
              max="50"
              step="0.5"
              value={cpiRate}
              onChange={(e) => setCpiRate(e.target.value)}
            />
          </InputRow>

          <InputRow label="Volatility">
            <p className="text-sm text-ink-faint">
              Fixed at 25% annual (Indian equity average)
            </p>
          </InputRow>

          <InputRow label="Paths">
            <p className="text-sm text-ink-faint">
              1,000 simulated trajectories
            </p>
          </InputRow>
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <Button onClick={handleRun} loading={running}>
            {running ? "Simulating…" : "Run Simulation"}
          </Button>
        </div>
      </Card>

      {/* ── Results ── */}
      {data && chartData && (
        <div className="mt-6">
          <h2 className="mb-3 font-display text-lg text-ink">
            Projection over {data.parameters_used.horizon_years} years
          </h2>

          {/* Metric cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-5">
              <MetricLabel>Median (p50)</MetricLabel>
              <div className="mt-3">
                <Money value={data.final_distribution.p50} size="lg" />
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Mean outcome</MetricLabel>
              <div className="mt-3">
                <Money value={data.final_distribution.mean} size="lg" />
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Pessimistic (p5)</MetricLabel>
              <div className="mt-3">
                <Money value={data.final_distribution.p5} size="lg" />
              </div>
              <p className="mt-1 text-xs text-ink-faint">5th percentile</p>
            </Card>
            <Card className="p-5">
              <MetricLabel>Optimistic (p95)</MetricLabel>
              <div className="mt-3">
                <Money value={data.final_distribution.p95} size="lg" />
              </div>
              <p className="mt-1 text-xs text-ink-faint">95th percentile</p>
            </Card>
          </div>

          {/* Fan chart */}
          <Card className="mt-6 p-5">
            <h3 className="mb-4 font-display text-base text-ink">Fan chart — percentile bands</h3>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-rule, #e5e7eb)" />
                  <XAxis
                    dataKey="year"
                    tick={{ fontSize: 11 }}
                    stroke="var(--color-ink-faint, #9ca3af)"
                  />
                  <YAxis
                    tickFormatter={formatChartINR}
                    tick={{ fontSize: 11 }}
                    stroke="var(--color-ink-faint, #9ca3af)"
                    width={70}
                  />
                  <Tooltip
                    formatter={(value) => formatChartINR(Number(value))}
                    contentStyle={{
                      backgroundColor: "var(--color-surface, #fff)",
                      border: "1px solid var(--color-rule, #e5e7eb)",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "11px" }}
                  />
                  {/* p5-p95 outermost band */}
                  <Area
                    type="monotone"
                    dataKey="p95"
                    stackId="band"
                    stroke="none"
                    fill="var(--color-brand, #6366f1)"
                    fillOpacity={0.08}
                    name="p95"
                  />
                  <Area
                    type="monotone"
                    dataKey="p75"
                    stackId="band2"
                    stroke="none"
                    fill="var(--color-brand, #6366f1)"
                    fillOpacity={0.15}
                    name="p75"
                  />
                  <Area
                    type="monotone"
                    dataKey="p50"
                    stackId="band3"
                    stroke="var(--color-brand, #6366f1)"
                    strokeWidth={2}
                    fill="var(--color-brand, #6366f1)"
                    fillOpacity={0.25}
                    name="Median (p50)"
                  />
                  <Area
                    type="monotone"
                    dataKey="p25"
                    stackId="band4"
                    stroke="none"
                    fill="var(--color-brand, #6366f1)"
                    fillOpacity={0.15}
                    name="p25"
                  />
                  <Area
                    type="monotone"
                    dataKey="p5"
                    stackId="band5"
                    stroke="none"
                    fill="var(--color-brand, #6366f1)"
                    fillOpacity={0.08}
                    name="p5"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Disclaimer */}
          <Card className="mt-4 p-4">
            <p className="flex items-start gap-2 text-xs text-ink-muted">
              <Badge tone="estimate">Not financial advice</Badge>
              <span>{data.disclaimer}</span>
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}

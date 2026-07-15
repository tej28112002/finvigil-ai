"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetch } from "@/lib/api";

// ── types ────────────────────────────────────────────────────────────────────

interface WhatIfTradeRow {
  symbol: string;
  trade_type: "buy" | "sell";
  quantity: string;
  price: string;
  execution_time: string; // datetime-local value: "YYYY-MM-DDTHH:mm"
}

interface ReplayHoldingSnapshot {
  instrument_id: string;
  symbol: string;
  quantity: string;
  avg_buy_price: string;
  invested_value: string;
}

interface ReplayResultData {
  as_of_date: string;
  holdings: ReplayHoldingSnapshot[];
  total_invested: string;
  realized_pnl_to_date: string;
  trades_replayed: number;
  what_if_trades_applied: number;
  disclaimer: string;
}

interface ReplayRunResponse {
  id: string;
  replay_scenario_id: string;
  result_data: ReplayResultData;
  created_at: string;
}

interface ReplayScenarioResponse {
  id: string;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function todayLocal() {
  return new Date().toISOString().slice(0, 10);
}

function blankTrade(): WhatIfTradeRow {
  const now = new Date();
  // datetime-local needs "YYYY-MM-DDTHH:mm"
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  return { symbol: "", trade_type: "buy", quantity: "", price: "", execution_time: local };
}

// ── sub-components ───────────────────────────────────────────────────────────

function InputRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
      <label className="w-36 shrink-0 text-xs font-medium uppercase tracking-wider text-ink-muted">
        {label}
      </label>
      <div className="flex-1">{children}</div>
    </div>
  );
}

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

function TradeRow({
  trade,
  index,
  onChange,
  onRemove,
}: {
  trade: WhatIfTradeRow;
  index: number;
  onChange: (i: number, field: keyof WhatIfTradeRow, value: string) => void;
  onRemove: (i: number) => void;
}) {
  return (
    <div className="grid grid-cols-[1fr_80px_90px_100px_1fr_32px] gap-2 items-center">
      <input
        className={inputCls}
        placeholder="Symbol e.g. RELIANCE"
        value={trade.symbol}
        onChange={(e) => onChange(index, "symbol", e.target.value.toUpperCase())}
      />
      <select
        className={inputCls}
        value={trade.trade_type}
        onChange={(e) => onChange(index, "trade_type", e.target.value)}
      >
        <option value="buy">Buy</option>
        <option value="sell">Sell</option>
      </select>
      <input
        className={inputCls}
        placeholder="Qty"
        type="number"
        min="0"
        step="1"
        value={trade.quantity}
        onChange={(e) => onChange(index, "quantity", e.target.value)}
      />
      <input
        className={inputCls}
        placeholder="Price ₹"
        type="number"
        min="0"
        step="0.01"
        value={trade.price}
        onChange={(e) => onChange(index, "price", e.target.value)}
      />
      <input
        className={inputCls}
        type="datetime-local"
        value={trade.execution_time}
        onChange={(e) => onChange(index, "execution_time", e.target.value)}
      />
      <button
        type="button"
        onClick={() => onRemove(index)}
        className="flex h-8 w-8 items-center justify-center rounded text-ink-muted hover:text-loss transition-colors"
        aria-label="Remove trade"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function ReplayClient() {
  const [asOfDate, setAsOfDate] = useState(todayLocal());
  const [scenarioName, setScenarioName] = useState("");
  const [whatIfTrades, setWhatIfTrades] = useState<WhatIfTradeRow[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReplayRunResponse | null>(null);

  // ── trade list helpers ──

  function addTrade() {
    setWhatIfTrades((prev) => [...prev, blankTrade()]);
  }

  function removeTrade(i: number) {
    setWhatIfTrades((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateTrade(i: number, field: keyof WhatIfTradeRow, value: string) {
    setWhatIfTrades((prev) =>
      prev.map((t, idx) => (idx === i ? { ...t, [field]: value } : t))
    );
  }

  // ── run ──

  async function handleRun() {
    setError(null);
    setResult(null);

    if (!asOfDate) {
      setError("Please pick a snapshot date.");
      return;
    }

    // Validate what-if trades
    for (let i = 0; i < whatIfTrades.length; i++) {
      const t = whatIfTrades[i];
      if (!t.symbol.trim()) { setError(`Trade ${i + 1}: symbol is required.`); return; }
      if (!t.quantity || Number(t.quantity) <= 0) { setError(`Trade ${i + 1}: quantity must be > 0.`); return; }
      if (!t.price || Number(t.price) <= 0) { setError(`Trade ${i + 1}: price must be > 0.`); return; }
      if (!t.execution_time) { setError(`Trade ${i + 1}: date/time is required.`); return; }
    }

    setRunning(true);
    try {
      const name = scenarioName.trim() || `Replay – ${asOfDate}`;

      // Step 1: create scenario
      const scenario = await apiFetch<ReplayScenarioResponse>("/replay/scenarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          parameters: {
            as_of_date: `${asOfDate}T23:59:59`,
            what_if_trades: whatIfTrades.map((t) => ({
              symbol: t.symbol.trim().toUpperCase(),
              trade_type: t.trade_type,
              quantity: t.quantity,
              price: t.price,
              execution_time: `${t.execution_time}:00`,
            })),
          },
        }),
      });

      // Step 2: run scenario
      const run = await apiFetch<ReplayRunResponse>(
        `/replay/scenarios/${scenario.id}/run`,
        { method: "POST" }
      );

      setResult(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    } finally {
      setRunning(false);
    }
  }

  const data = result?.result_data;

  return (
    <div className="mx-auto max-w-5xl">
      {/* Page header */}
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Portfolio Replay</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Reconstruct your portfolio at any past date, then layer in hypothetical trades to model different outcomes.
        </p>
      </div>

      {/* ── Configuration card ── */}
      <Card className="p-5">
        <h2 className="mb-4 font-display text-base text-ink">Configuration</h2>

        <div className="space-y-4">
          <InputRow label="Snapshot date">
            <input
              type="date"
              className={inputCls}
              value={asOfDate}
              max={todayLocal()}
              onChange={(e) => setAsOfDate(e.target.value)}
            />
          </InputRow>

          <InputRow label="Scenario name">
            <input
              type="text"
              className={inputCls}
              placeholder={`Replay – ${asOfDate}`}
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
            />
          </InputRow>
        </div>

        {/* What-if trades */}
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">
              What-if trades <Badge tone="neutral">{whatIfTrades.length}</Badge>
            </p>
            <Button variant="secondary" onClick={addTrade} className="h-7 px-3 text-xs">
              + Add trade
            </Button>
          </div>

          {whatIfTrades.length === 0 ? (
            <p className="rounded-md border border-dashed border-rule px-4 py-5 text-center text-sm text-ink-faint">
              No what-if trades added — the replay will use only your real trade history.
            </p>
          ) : (
            <div className="space-y-2">
              {/* Column headers */}
              <div className="grid grid-cols-[1fr_80px_90px_100px_1fr_32px] gap-2 px-0">
                {["Symbol", "Type", "Qty", "Price", "Date & time", ""].map((h) => (
                  <span key={h} className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">
                    {h}
                  </span>
                ))}
              </div>
              {whatIfTrades.map((t, i) => (
                <TradeRow
                  key={i}
                  trade={t}
                  index={i}
                  onChange={updateTrade}
                  onRemove={removeTrade}
                />
              ))}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )}

        {/* Run button */}
        <div className="mt-5 flex justify-end">
          <Button onClick={handleRun} loading={running}>
            {running ? "Running…" : "Run Replay"}
          </Button>
        </div>
      </Card>

      {/* ── Results ── */}
      {data && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="font-display text-lg text-ink">
              Snapshot as of {fmtDate(data.as_of_date)}
            </h2>
            {data.what_if_trades_applied > 0 && (
              <Badge tone="brand">{data.what_if_trades_applied} what-if trade{data.what_if_trades_applied !== 1 ? "s" : ""} applied</Badge>
            )}
          </div>

          {/* Metric cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card className="p-5">
              <MetricLabel>Total invested</MetricLabel>
              <div className="mt-3">
                <Money value={data.total_invested} size="lg" />
              </div>
              <p className="mt-1 text-xs text-ink-faint">FIFO cost basis</p>
            </Card>
            <Card className="p-5">
              <MetricLabel>Realized P&amp;L to date</MetricLabel>
              <div className="mt-3">
                <Money value={data.realized_pnl_to_date} size="lg" tone="auto" signed />
              </div>
              <p className="mt-1 text-xs text-ink-faint">On closed positions only</p>
            </Card>
            <Card className="p-5">
              <MetricLabel>Trades replayed</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-ink">
                {data.trades_replayed}
              </div>
              <p className="mt-1 text-xs text-ink-faint">Real trades processed</p>
            </Card>
          </div>

          {/* Holdings table */}
          <div className="mt-6">
            <h3 className="font-display mb-2 text-base text-ink">Holdings breakdown</h3>

            {data.holdings.length === 0 ? (
              <EmptyState
                icon={
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12 2 2 7l10 5 10-5-10-5Z" />
                    <path d="m2 17 10 5 10-5" />
                    <path d="m2 12 10 5 10-5" />
                  </svg>
                }
                title="No open holdings at this date"
                description="All positions had been closed by the selected date, or no trades exist before it."
              />
            ) : (
              <Table>
                <THead>
                  <Th>Symbol</Th>
                  <Th align="right">Qty held</Th>
                  <Th align="right">Avg buy price</Th>
                  <Th align="right">Invested value</Th>
                </THead>
                <tbody>
                  {data.holdings.map((h) => (
                    <Tr key={h.instrument_id}>
                      <Td className="font-medium">{h.symbol}</Td>
                      <Td align="right" className="font-mono">{h.quantity}</Td>
                      <Td align="right">
                        <Money value={h.avg_buy_price} size="sm" />
                      </Td>
                      <Td align="right">
                        <Money value={h.invested_value} size="sm" />
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>

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

"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";

interface PortfolioItem {
  instrument_id: string;
  symbol: string;
  instrument_type: string;
  total_quantity: string;
  average_buy_price: string;
  total_invested: string;
}

interface HoldingLot {
  instrument_id: string;
  broker_connection_id: string;
}

interface BrokerConnection {
  id: string;
  broker_name: string;
}

interface FnoPosition {
  instrument_id: string;
  symbol: string;
  open_quantity: string;
  avg_buy_price: string;
}

type Tab = "equity" | "fno" | "crypto";

/**
 * Dashboard holdings table (BRD §8.1). "Current" and "P&L" columns are
 * deliberately absent — no backend endpoint returns per-instrument live
 * price (see Stage 2B gap #1, approved: cost-basis columns only). The F&O
 * tab has no per-lot broker attribution in FnoOpenPositionResponse, so its
 * column set is intentionally narrower rather than faking a broker badge.
 */
export function HoldingsTable({
  portfolio,
  holdings,
  brokers,
  fnoPositions,
  brokerFilter,
}: {
  portfolio: PortfolioItem[];
  holdings: HoldingLot[];
  brokers: BrokerConnection[];
  fnoPositions: FnoPosition[];
  brokerFilter: string | null;
}) {
  const [tab, setTab] = useState<Tab>("equity");

  const brokerNameById = useMemo(
    () => new Map(brokers.map((b) => [b.id, b.broker_name])),
    [brokers]
  );

  // instrument_id -> broker_name(s) present in its lots, for the badge + filter.
  const brokersByInstrument = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const lot of holdings) {
      const name = brokerNameById.get(lot.broker_connection_id);
      if (!name) continue;
      if (!map.has(lot.instrument_id)) map.set(lot.instrument_id, new Set());
      map.get(lot.instrument_id)!.add(name);
    }
    return map;
  }, [holdings, brokerNameById]);

  const equityAndCrypto = useMemo(
    () =>
      portfolio.filter((p) => {
        if (tab === "fno") return false;
        if (p.instrument_type !== tab) return false;
        if (!brokerFilter) return true;
        const names = brokersByInstrument.get(p.instrument_id);
        return names?.has(brokerFilter) ?? false;
      }),
    [portfolio, tab, brokerFilter, brokersByInstrument]
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "equity", label: "Equity" },
    { key: "fno", label: "F&O" },
    { key: "crypto", label: "Crypto" },
  ];

  return (
    <div>
      <div className="mb-3 flex gap-1 border-b border-rule">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            aria-current={tab === t.key ? "page" : undefined}
            className={`cursor-pointer border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-brand text-brand"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "fno" ? (
        fnoPositions.length === 0 ? (
          <EmptyState
            title="No open F&O positions"
            description="Open futures & options positions will appear here once you have unmatched F&O buys."
          />
        ) : (
          <Table>
            <THead>
              <Th>Symbol</Th>
              <Th align="right">Qty</Th>
              <Th align="right">Avg buy</Th>
            </THead>
            <tbody>
              {fnoPositions.map((p) => (
                <Tr key={p.instrument_id}>
                  <Td className="font-medium">{p.symbol}</Td>
                  <Td align="right" className="font-mono">{p.open_quantity}</Td>
                  <Td align="right"><Money value={p.avg_buy_price} size="sm" /></Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )
      ) : equityAndCrypto.length === 0 ? (
        <EmptyState
          title={`No ${tab} holdings`}
          description={`${tab === "equity" ? "Equity" : "Crypto"} positions will appear here once trades are synced or imported.`}
        />
      ) : (
        <Table>
          <THead>
            <Th>Instrument</Th>
            <Th>Broker</Th>
            <Th align="right">Qty</Th>
            <Th align="right">Avg cost</Th>
            <Th align="right">Invested</Th>
          </THead>
          <tbody>
            {equityAndCrypto.map((item) => {
              const names = brokersByInstrument.get(item.instrument_id);
              return (
                <Tr key={item.instrument_id}>
                  <Td className="font-medium">{item.symbol}</Td>
                  <Td>
                    {names && names.size > 0 ? (
                      <Badge tone="neutral">{[...names].join(", ")}</Badge>
                    ) : (
                      <span className="text-ink-faint">—</span>
                    )}
                  </Td>
                  <Td align="right" className="font-mono">{item.total_quantity}</Td>
                  <Td align="right"><Money value={item.average_buy_price} size="sm" /></Td>
                  <Td align="right"><Money value={item.total_invested} size="sm" /></Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}

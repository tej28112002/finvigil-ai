"use client";

import { Fragment, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";

interface PortfolioItem {
  instrument_id: string; symbol: string; instrument_type: string;
  total_quantity: string; total_invested: string;
  average_buy_price: string; lot_count: number;
}
interface HoldingLot {
  id: string; instrument_id: string; quantity_bought: string;
  quantity_remaining: string; buy_price: string; buy_date: string; status: string;
}

const typeBadgeTone: Record<string, "brand" | "neutral"> = {
  equity: "brand", crypto: "neutral",
};

function statusTone(status: string): "gain" | "estimate" | "neutral" {
  if (status === "open") return "gain";
  if (status === "partial") return "estimate";
  return "neutral";
}

export function PortfolioTable({ items, lots }: { items: PortfolioItem[]; lots: HoldingLot[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <Table>
      <THead>
        <Th>Instrument</Th>
        <Th align="right">Qty</Th>
        <Th align="right">Avg cost</Th>
        <Th align="right">Invested</Th>
        <Th align="right">Lots</Th>
      </THead>
      <tbody>
        {items.map((item) => {
          const isOpen = expanded === item.instrument_id;
          const itemLots = lots.filter((l) => l.instrument_id === item.instrument_id);
          return (
            <Fragment key={item.instrument_id}>
              <Tr>
                <Td>
                  <button
                    type="button"
                    onClick={() => setExpanded(isOpen ? null : item.instrument_id)}
                    className="flex cursor-pointer items-center gap-2 text-left"
                    aria-expanded={isOpen}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                      className={`shrink-0 text-ink-faint transition-transform ${isOpen ? "rotate-90" : ""}`} aria-hidden="true">
                      <path d="m9 6 6 6-6 6" />
                    </svg>
                    <span className="font-medium text-ink">{item.symbol}</span>
                    <Badge tone={typeBadgeTone[item.instrument_type] ?? "neutral"}>
                      {item.instrument_type}
                    </Badge>
                  </button>
                </Td>
                <Td align="right" className="font-mono">{item.total_quantity}</Td>
                <Td align="right"><Money value={item.average_buy_price} size="sm" /></Td>
                <Td align="right"><Money value={item.total_invested} size="sm" /></Td>
                <Td align="right" className="text-ink-muted">{item.lot_count}</Td>
              </Tr>
              {isOpen && (
                <tr>
                  <td colSpan={5} className="bg-bg px-4 py-3">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-faint">FIFO lots</p>
                    <div className="space-y-1.5">
                      {itemLots.map((lot) => (
                        <div key={lot.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-rule bg-surface px-3 py-2 text-sm">
                          <span className="text-ink-muted">{new Date(lot.buy_date).toLocaleDateString("en-IN")}</span>
                          <span className="font-mono text-ink">{lot.quantity_remaining} / {lot.quantity_bought} qty</span>
                          <Money value={lot.buy_price} size="sm" />
                          <Badge tone={statusTone(lot.status)}>{lot.status}</Badge>
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </Table>
  );
}

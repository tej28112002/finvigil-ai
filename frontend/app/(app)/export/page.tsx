"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AYSelector } from "@/components/ui/ay-selector";
import { DEFAULT_AY } from "@/lib/ay";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { apiFetch } from "@/lib/api";
import { onboarding } from "@/lib/onboarding";
import { createClient } from "@/lib/supabase/client";

interface TransactionDetail {
  symbol: string;
  isin: string | null;
  quantity_sold: string;
  buy_date: string;
  sell_date: string;
  buy_price: string;
  sell_price: string;
  holding_days: number;
  gain_type: string;
  profit_loss: string;
}

interface CapitalGainsSummary {
  total_stcg_gains: string;
  total_ltcg_gains: string;
  taxable_stcg: string;
  taxable_ltcg: string;
  stcg_tax_estimate: string;
  ltcg_tax_estimate: string;
  total_tax_estimate: string;
  ltcg_exemption_applied: string;
}

interface CapitalGainsExport {
  export_id: string;
  assessment_year: string;
  generated_at: string;
  disclaimer: string;
  summary: CapitalGainsSummary;
  transactions: TransactionDetail[];
}

function ExportPageInner() {
  const params = useSearchParams();
  const [ay, setAy] = useState(params.get("ay") ?? DEFAULT_AY);
  const [result, setResult] = useState<CapitalGainsExport | null>(null);
  const [generating, setGenerating] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const data = await apiFetch<CapitalGainsExport>("/tax/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assessment_year: ay }),
      });
      setResult(data);
      onboarding.markExportedCA();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not generate the export"
      );
    } finally {
      setGenerating(false);
    }
  }

  // The on-page summary above is generated JSON (POST /tax/export) --
  // useful as a preview, but the actual downloadable artifact should be
  // the real ZIP bundle (POST /tax/ca-bundle) the dashboard's CA Export
  // card promises, not a re-serialization of that preview JSON.
  async function handleDownload() {
    setDownloadingZip(true);
    setError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        window.location.href = "/login";
        return;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tax/ca-bundle`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ assessment_year: ay }),
      });

      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        let detail = `Request failed (${res.status})`;
        try {
          const body = await res.json();
          if (typeof body?.detail === "string") detail = body.detail;
        } catch {
          // non-JSON error body — keep the generic message
        }
        throw new Error(detail);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().slice(0, 10);
      a.download = `finvigil-ca-bundle-${today}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not download the CA bundle"
      );
    } finally {
      setDownloadingZip(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <AYSelector value={ay} onChange={setAy} />
        <div className="flex gap-2">
          {result && (
            <Button variant="secondary" onClick={handleDownload} loading={downloadingZip}>
              Download CA Bundle (ZIP)
            </Button>
          )}
          <Button onClick={handleGenerate} loading={generating}>
            {result ? "Regenerate" : "Generate CA report"}
          </Button>
        </div>
      </div>

      {error && (
        <Card className="mb-4 p-4">
          <p className="text-sm text-loss" role="alert">
            {error}
          </p>
        </Card>
      )}

      {!result ? (
        <Card className="flex flex-col items-center px-6 py-14 text-center">
          <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-brand-soft text-brand">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
          </div>
          <p className="font-display text-lg text-ink">
            A capital-gains report your CA can actually use
          </p>
          <p className="mt-1.5 max-w-sm text-sm text-ink-muted">
            Generates a per-transaction breakdown for AY {ay} — symbols,
            buy/sell dates, holding period, STCG/LTCG split, and estimated
            tax. Not a government-uploadable file.
          </p>
          <Button onClick={handleGenerate} loading={generating} className="mt-5">
            Generate CA report
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-5">
              <MetricLabel>Taxable STCG</MetricLabel>
              <div className="mt-3">
                <Money value={result.summary.taxable_stcg} size="lg" />
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Taxable LTCG</MetricLabel>
              <div className="mt-3">
                <Money value={result.summary.taxable_ltcg} size="lg" />
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Total tax estimate</MetricLabel>
              <div className="mt-3">
                <Money value={result.summary.total_tax_estimate} size="lg" />
              </div>
            </Card>
            <Card className="p-5">
              <MetricLabel>Transactions</MetricLabel>
              <div className="mt-3 font-mono text-2xl font-medium text-ink">
                {result.transactions.length}
              </div>
            </Card>
          </div>

          {result.transactions.length > 0 && (
            <div className="mt-6">
              <Table>
                <THead>
                  <Th>Symbol</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">Buy</Th>
                  <Th align="right">Sell</Th>
                  <Th align="right">Days</Th>
                  <Th>Type</Th>
                  <Th align="right">P&amp;L</Th>
                </THead>
                <tbody>
                  {result.transactions.map((t, i) => (
                    <Tr key={i}>
                      <Td className="font-medium">{t.symbol}</Td>
                      <Td align="right" className="font-mono">{t.quantity_sold}</Td>
                      <Td align="right"><Money value={t.buy_price} size="sm" /></Td>
                      <Td align="right"><Money value={t.sell_price} size="sm" /></Td>
                      <Td align="right" className="text-ink-muted">{t.holding_days}</Td>
                      <Td>
                        <Badge tone={t.gain_type === "LTCG" ? "brand" : "neutral"}>
                          {t.gain_type}
                        </Badge>
                      </Td>
                      <Td align="right"><Money value={t.profit_loss} size="sm" tone="auto" signed /></Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}

          <Card className="mt-6 p-4">
            <p className="flex items-start gap-2 text-xs text-ink-muted">
              <Badge tone="estimate">Not a government filing</Badge>
              <span>{result.disclaimer}</span>
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

export default function ExportPage() {
  return (
    <Suspense fallback={null}>
      <ExportPageInner />
    </Suspense>
  );
}

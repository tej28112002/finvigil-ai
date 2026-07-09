import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { apiFetchServer } from "@/lib/api-server";
import { DEFAULT_AY } from "@/lib/ay";
import { AYSelectorURL } from "@/app/(app)/crypto/ay-selector-url";

interface CryptoTax {
  assessment_year: string; transaction_count: number;
  total_vda_gains: string; total_vda_losses: string;
  taxable_vda_income: string; vda_tax_rate: string; vda_tax: string;
  total_tds_paid: string; net_tax_payable: string; disclaimer: string;
}

export default async function CryptoPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay = DEFAULT_AY } = await searchParams;
  const data = await apiFetchServer<CryptoTax>(`/crypto/tax/${ay}`);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <AYSelectorURL ay={ay} basePath="/crypto" />
      </div>

      {!data || data.transaction_count === 0 ? (
        <EmptyState
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M9.5 8.5h4a1.75 1.75 0 0 1 0 3.5h-4m0 0h4.5a1.75 1.75 0 0 1 0 3.5H9.5M11 6.5v11" />
            </svg>
          }
          title={`No crypto activity in AY ${ay}`}
          description="VDA gains and losses will appear here once crypto trades are recorded for this assessment year."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="p-5">
            <MetricLabel>VDA gains</MetricLabel>
            <div className="mt-3"><Money value={data.total_vda_gains} size="lg" tone="auto" signed /></div>
          </Card>
          <Card className="p-5">
            <MetricLabel>Disclosed losses</MetricLabel>
            <div className="mt-3"><Money value={data.total_vda_losses} size="lg" tone="auto" /></div>
            <p className="mt-1 text-xs text-ink-faint">Not deductible — no set-off</p>
          </Card>
          <Card className="p-5">
            <MetricLabel>Taxable VDA income</MetricLabel>
            <div className="mt-3"><Money value={data.taxable_vda_income} size="lg" /></div>
          </Card>
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <MetricLabel>Tax at 30%</MetricLabel>
              <Badge tone="loss">Flat</Badge>
            </div>
            <div className="mt-3"><Money value={data.vda_tax} size="lg" /></div>
          </Card>
          <Card className="p-5">
            <MetricLabel>TDS credit</MetricLabel>
            <div className="mt-3"><Money value={data.total_tds_paid} size="lg" /></div>
            <p className="mt-1 text-xs text-ink-faint">Section 194S, 1% at source</p>
          </Card>
          <Card className="p-5">
            <MetricLabel>Net payable</MetricLabel>
            <div className="mt-3"><Money value={data.net_tax_payable} size="lg" tone="auto" signed /></div>
          </Card>
        </div>
      )}

      <Card className="mt-6 p-4">
        <p className="flex items-start gap-2 text-xs text-ink-muted">
          <Badge tone="estimate">Estimate</Badge>
          <span>{data?.disclaimer ?? "VDA tax is a capital gains estimate under Section 115BBH and excludes cess, surcharge, and other income."}</span>
        </p>
      </Card>
    </div>
  );
}

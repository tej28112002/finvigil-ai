import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { apiFetchServer, getServerToken } from "@/lib/api-server";
import { DEFAULT_AY } from "@/lib/ay";
import { sumToPaise, decimalSign } from "@/lib/format";
import { TaxActions } from "@/app/(app)/tax/tax-actions";

interface TaxSummary {
  assessment_year: string; total_stcg_gains: string; total_ltcg_gains: string;
  taxable_stcg: string; taxable_ltcg: string; stcg_tax: string; ltcg_tax: string;
  total_tax_liability: string; disclaimer: string;
}
interface FnoPnl {
  total_pnl: string; intraday_pnl: string; positional_pnl: string;
  realized_entry_count: number;
}
interface CryptoTax {
  total_vda_gains: string; total_vda_losses: string; vda_tax: string;
  total_tds_paid: string; net_tax_payable: string; disclaimer: string;
}

export default async function TaxPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay = DEFAULT_AY } = await searchParams;
  const token = await getServerToken();

  const [fno, crypto, equity] = await Promise.all([
    apiFetchServer<FnoPnl>(`/fno/pnl/${ay}`, token),
    apiFetchServer<CryptoTax>(`/crypto/tax/${ay}`, token),
    apiFetchServer<TaxSummary>(`/tax/summary/${ay}`, token),
  ]);

  const equityTaxPaise = equity ? sumToPaise([equity.total_tax_liability]) : 0n;
  const cryptoNetPaise = crypto ? sumToPaise([crypto.net_tax_payable]) : 0n;
  const combinedPaise = equityTaxPaise + cryptoNetPaise;
  const fnoTone = fno ? decimalSign(fno.total_pnl) : 0;
  const equityMissing = equity === null;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        {/* AY selector + Export + Calculate button — needs client for URL push & POST */}
        <TaxActions ay={ay} equityMissing={equityMissing} />
      </div>

      {/* Combined estimate */}
      <Card className="mb-4 p-6">
        <MetricLabel>Estimated tax liability — equity + crypto, AY {ay}</MetricLabel>
        <div className="mt-3">
          <Money value={combinedPaise} size="xl" />
        </div>
        <p className="mt-2 text-xs text-ink-faint">
          Crypto figure is net of TDS already deducted. F&amp;O business income is
          shown separately below — its tax rate depends on your total income slab.
        </p>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Equity STCG */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <MetricLabel>Equity STCG</MetricLabel>
            <Badge tone="brand">20%</Badge>
          </div>
          {equityMissing ? (
            <p className="mt-3 text-sm text-ink-muted">Not calculated yet for AY {ay}.</p>
          ) : (
            <>
              <div className="mt-3"><Money value={equity!.total_stcg_gains} size="lg" tone="auto" signed /></div>
              <p className="mt-1 text-xs text-ink-faint">
                Taxable: <Money value={equity!.taxable_stcg} size="sm" /> · Tax: <Money value={equity!.stcg_tax} size="sm" />
              </p>
            </>
          )}
        </Card>

        {/* Equity LTCG */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <MetricLabel>Equity LTCG</MetricLabel>
            <Badge tone="brand">12.5%</Badge>
          </div>
          {equityMissing ? (
            <p className="mt-3 text-sm text-ink-muted">Not calculated yet.</p>
          ) : (
            <>
              <div className="mt-3"><Money value={equity!.total_ltcg_gains} size="lg" tone="auto" signed /></div>
              <p className="mt-1 text-xs text-ink-faint">
                After ₹1,25,000 exemption — taxable: <Money value={equity!.taxable_ltcg} size="sm" /> · Tax: <Money value={equity!.ltcg_tax} size="sm" />
              </p>
            </>
          )}
        </Card>

        {/* F&O */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <MetricLabel>F&amp;O business income</MetricLabel>
            <Badge tone="neutral">PGBP</Badge>
          </div>
          {fno && (
            <>
              <div className="mt-3"><Money value={fno.total_pnl} size="lg" tone="auto" signed /></div>
              <p className="mt-1 text-xs text-ink-faint">
                {fnoTone < 0
                  ? "A loss can be carried forward — consult your CA."
                  : `${fno.realized_entry_count} realized entries this year.`}
              </p>
            </>
          )}
        </Card>

        {/* Crypto */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <MetricLabel>Crypto / VDA</MetricLabel>
            <Badge tone="loss">30% flat</Badge>
          </div>
          {crypto && (
            <>
              <div className="mt-3"><Money value={crypto.vda_tax} size="lg" /></div>
              <p className="mt-1 text-xs text-ink-faint">
                No set-off on losses · TDS credit <Money value={crypto.total_tds_paid} size="sm" />
              </p>
            </>
          )}
        </Card>
      </div>

      <Card className="mt-4 p-4">
        <p className="flex items-start gap-2 text-xs text-ink-muted">
          <Badge tone="estimate">Estimate</Badge>
          <span>{equity?.disclaimer ?? crypto?.disclaimer ?? "Capital gains figures are estimates only and exclude cess, surcharge, and other income."}</span>
        </p>
      </Card>
    </div>
  );
}

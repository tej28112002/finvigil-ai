import Link from "next/link";
import { Card, MetricLabel } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { sumToPaise } from "@/lib/format";

interface Props {
  equityTax: string | null; // null = not calculated yet for this AY
  cryptoNetTax: string | null;
  fnoPnl: string | null;
  assessmentYear: string;
}

/**
 * Tax meter (Idea 7). Combines equity total_tax_liability + crypto
 * net_tax_payable (net of TDS, avoids double-counting — see Stage 2B
 * proposal). F&O shown as context only: no backend service computes F&O's
 * actual tax liability (it depends on the filer's income slab), so it's
 * never folded into the combined estimate.
 */
export function TaxMeterCard({ equityTax, cryptoNetTax, fnoPnl, assessmentYear }: Props) {
  if (equityTax === null) {
    return (
      <Card className="p-5">
        <MetricLabel>Tax liability so far this FY</MetricLabel>
        <p className="mt-3 text-sm text-ink-muted">
          Not calculated yet for AY {assessmentYear}.
        </p>
        <Link
          href="/tax"
          className="mt-2 inline-block text-sm font-medium text-brand hover:text-brand-hover"
        >
          Calculate on the Tax page →
        </Link>
      </Card>
    );
  }

  const combinedPaise = sumToPaise([equityTax, cryptoNetTax ?? "0"]);

  return (
    <Card className="p-5">
      <MetricLabel>Tax liability so far this FY</MetricLabel>
      <div className="mt-3">
        <Money value={combinedPaise} size="lg" />
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-ink-faint">
        <span>
          Equity <Money value={equityTax} size="sm" />
        </span>
        {cryptoNetTax !== null && (
          <span>
            Crypto <Money value={cryptoNetTax} size="sm" />
          </span>
        )}
        {fnoPnl !== null && (
          <span>
            F&amp;O P&amp;L <Money value={fnoPnl} size="sm" tone="auto" signed /> (not
            taxed here)
          </span>
        )}
      </div>
    </Card>
  );
}

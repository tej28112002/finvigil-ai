import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, THead, Th, Td, Tr } from "@/components/ui/table";
import { FaqAccordion } from "./faq-accordion";
import { COMPARISON_ROWS, PRICING_FAQS, PRICING_PLANS } from "./pricing-data";

export const metadata: Metadata = {
  title: "Pricing — FinVigil",
  description:
    "Simple, transparent pricing for FinVigil's portfolio intelligence and tax clarity platform.",
};

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-brand" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

export default function PricingPage() {
  return (
    <>
      {/* Header */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 text-ink opacity-[0.03]"
          style={{
            backgroundImage: "radial-gradient(currentColor 1.2px, transparent 1.2px)",
            backgroundSize: "26px 26px",
          }}
          aria-hidden="true"
        />
        <div className="relative mx-auto max-w-3xl px-6 py-16 text-center lg:py-20">
          <p className="text-sm font-medium text-ink-faint">Pricing</p>
          <h1 className="font-display mt-4 text-4xl leading-[1.08] text-ink sm:text-5xl">
            Simple pricing.
            <br />
            <span className="italic text-brand">No tax surprises.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-md text-base text-ink-muted">
            Start free. Upgrade when you need the full tax engine, AIS reconciliation,
            or a CA-ready export.
          </p>
        </div>
      </section>

      {/* Plan cards */}
      <section className="border-t border-rule bg-surface">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:py-20">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {PRICING_PLANS.map((plan) => (
              <Card
                key={plan.name}
                className={`relative flex flex-col p-6 ${plan.featured ? "border-2 border-brand shadow-token-lg" : ""}`}
              >
                {plan.badge && (
                  <span className="absolute -top-3 left-6">
                    <Badge tone="brand">{plan.badge}</Badge>
                  </span>
                )}

                <h3 className="font-display text-lg text-ink">{plan.name}</h3>

                <div className="mt-3 flex items-baseline gap-1">
                  <span className="font-display text-3xl text-ink">{plan.price}</span>
                  <span className="text-sm text-ink-faint">{plan.cadence}</span>
                </div>

                {plan.equivalentMonthly && (
                  <p className="mt-1 text-xs text-ink-faint">{plan.equivalentMonthly}</p>
                )}
                {plan.savings && (
                  <p className="mt-1 text-xs font-medium text-gain">{plan.savings}</p>
                )}

                <ul className="mt-5 flex-1 space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-ink-muted">
                      <CheckIcon />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                <Link href="/login" className="mt-6 block">
                  <Button
                    variant={plan.featured ? "primary" : "secondary"}
                    className="h-10 w-full"
                  >
                    {plan.name === "Free" ? "Get started" : "Upgrade"}
                  </Button>
                </Link>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Feature comparison table */}
      <section className="border-t border-rule">
        <div className="mx-auto max-w-4xl px-6 py-16 lg:py-20">
          <h2 className="font-display max-w-lg text-3xl text-ink lg:text-4xl">
            Compare plans in detail.
          </h2>
          <div className="mt-10">
            <Table>
              <THead>
                <Th>Feature</Th>
                <Th align="right">Free</Th>
                <Th align="right">Pro</Th>
                <Th align="right">Premium</Th>
              </THead>
              <tbody>
                {COMPARISON_ROWS.map((row) => (
                  <Tr key={row.feature}>
                    <Td className="font-medium">{row.feature}</Td>
                    <Td align="right" className="font-mono">{row.free}</Td>
                    <Td align="right" className="font-mono">{row.pro}</Td>
                    <Td align="right" className="font-mono">{row.premium}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-rule bg-surface">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center lg:py-20">
          <h2 className="font-display text-3xl text-ink lg:text-4xl">
            Frequently asked questions.
          </h2>
          <div className="mt-10 text-left">
            <FaqAccordion items={PRICING_FAQS} />
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="border-t border-rule">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:py-20">
          <div className="relative overflow-hidden rounded-2xl bg-brand px-8 py-14 text-center text-brand-fg shadow-token-lg lg:px-16">
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.12]"
              style={{
                backgroundImage: "radial-gradient(currentColor 1.2px, transparent 1.2px)",
                backgroundSize: "22px 22px",
              }}
              aria-hidden="true"
            />
            <div className="relative">
              <h2 className="font-display mx-auto max-w-xl text-3xl leading-tight lg:text-4xl">
                Ready to see your one number?
              </h2>
              <div className="mt-8 flex justify-center">
                <Link href="/login">
                  <Button
                    variant="secondary"
                    className="h-11 border-transparent bg-brand-fg px-7 text-base text-brand hover:bg-brand-fg hover:opacity-90"
                  >
                    Get started
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

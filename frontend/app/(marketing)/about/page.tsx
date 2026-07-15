import type { Metadata } from "next";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrustSection } from "@/components/marketing/trust-section";

export const metadata: Metadata = {
  title: "About — FinVigil",
  description:
    "FinVigil is a read-only portfolio intelligence and tax clarity platform for Indian investors and traders.",
};

interface AboutFeature {
  title: string;
  description: string;
  icon: React.ReactNode;
}

function icon(paths: React.ReactNode) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  );
}

const FEATURES: AboutFeature[] = [
  {
    title: "Consolidate",
    description: "Every broker, every asset class — equity, F&O, mutual funds, crypto — pulled into one FIFO-tracked portfolio.",
    icon: icon(
      <>
        <path d="M12 2 2 7l10 5 10-5-10-5Z" />
        <path d="m2 17 10 5 10-5" />
        <path d="m2 12 10 5 10-5" />
      </>
    ),
  },
  {
    title: "Reconcile",
    description: "AIS reconciliation catches mismatches between what the tax department has on file and what you actually traded, before you file.",
    icon: icon(
      <>
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </>
    ),
  },
  {
    title: "Compute",
    description: "Equity STCG/LTCG, F&O business income, and crypto VDA tax — computed automatically, the moment a trade settles.",
    icon: icon(
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" />
        <path d="M14 2v6h6" />
        <path d="m9 16 6-6" />
      </>
    ),
  },
  {
    title: "Export",
    description: "A CA-ready ZIP bundle and ITR-3 schedule export — transaction-level detail, not just a summary number.",
    icon: icon(
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </>
    ),
  },
];

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
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
          <p className="text-sm font-medium text-ink-faint">About FinVigil</p>
          <h1 className="font-display mt-4 text-4xl leading-[1.08] text-ink sm:text-5xl">
            Built for Indian investors who&apos;d rather trade than
            <span className="italic text-brand"> wrangle spreadsheets.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base text-ink-muted">
            FinVigil is a read-only portfolio intelligence platform: it consolidates
            your holdings across brokers, reconciles them against your AIS, and
            computes your equity, F&amp;O, and crypto tax — so tax season is a
            formality, not a scramble. FinVigil never places, modifies, or cancels
            a trade. It only shows you what&apos;s already true about your own
            portfolio.
          </p>
        </div>
      </section>

      {/* 4 feature cards */}
      <section className="border-t border-rule bg-surface">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:py-20">
          <h2 className="font-display max-w-lg text-3xl text-ink lg:text-4xl">
            What FinVigil does.
          </h2>
          <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <Card key={f.title} interactive className="p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-rule bg-brand-soft text-brand">
                  {f.icon}
                </div>
                <h3 className="font-display mt-4 text-base text-ink">{f.title}</h3>
                <p className="mt-2 text-sm text-ink-muted">{f.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 3 trust signals — reuses the same TrustSection shown on the homepage */}
      <TrustSection />

      {/* CTA */}
      <section className="border-t border-rule">
        <div className="mx-auto max-w-7xl px-6 py-16 text-center lg:py-20">
          <h2 className="font-display mx-auto max-w-lg text-3xl text-ink lg:text-4xl">
            See your complete tax picture in under two minutes.
          </h2>
          <div className="mt-8 flex justify-center">
            <Link href="/login">
              <Button variant="primary" className="h-11 px-7 text-base">
                Get started
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

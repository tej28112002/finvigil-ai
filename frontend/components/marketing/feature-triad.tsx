import { Card } from "@/components/ui/card";

interface Feature {
  title: string;
  description: string;
  illustration: React.ReactNode;
}

/**
 * Each feature gets a small composed line-illustration (not a single bare
 * glyph) drawn in the brand color on a brand-soft panel — richer than an
 * icon, still restrained enough for a finance product. All CSS/SVG, both
 * themes via tokens.
 */
function IllustrationFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-28 items-center justify-center rounded-lg border border-rule bg-brand-soft text-brand">
      {children}
    </div>
  );
}

const FEATURES: Feature[] = [
  {
    title: "Multi-broker consolidation",
    description:
      "Zerodha, Angel One, Upstox and more — every holding pulled into one FIFO-tracked portfolio, one total value.",
    illustration: (
      <svg width="120" height="72" viewBox="0 0 120 72" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {/* three sources converging into one node */}
        <rect x="4" y="8" width="30" height="12" rx="3" />
        <rect x="4" y="30" width="30" height="12" rx="3" />
        <rect x="4" y="52" width="30" height="12" rx="3" />
        <path d="M34 14 Q64 14 74 36" opacity="0.6" />
        <path d="M34 36 L74 36" opacity="0.6" />
        <path d="M34 58 Q64 58 74 36" opacity="0.6" />
        <circle cx="86" cy="36" r="12" fill="currentColor" fillOpacity="0.12" />
        <circle cx="86" cy="36" r="12" />
        <path d="M81 36l3.5 3.5L92 32" />
      </svg>
    ),
  },
  {
    title: "Automatic tax engine",
    description:
      "Equity STCG at 20% and LTCG at 12.5%, F&O as business income, crypto VDA at a flat 30% — computed the moment a trade settles.",
    illustration: (
      <svg width="120" height="72" viewBox="0 0 120 72" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {/* document with a computed figure */}
        <path d="M30 6h40l14 14v46a2 2 0 0 1-2 2H30a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" />
        <path d="M70 6v14h14" />
        <path d="M38 34h24" opacity="0.55" />
        <path d="M38 44h30" opacity="0.55" />
        <path d="M38 54h18" opacity="0.55" />
        <circle cx="74" cy="52" r="10" fill="currentColor" fillOpacity="0.12" />
        <path d="M70 52h8M74 48v8" />
      </svg>
    ),
  },
  {
    title: "CA-ready export",
    description:
      "A capital-gains report your CA can actually file from — per-transaction detail, not just a summary number.",
    illustration: (
      <svg width="120" height="72" viewBox="0 0 120 72" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {/* stacked rows exporting down into a tray */}
        <rect x="34" y="8" width="52" height="9" rx="2" opacity="0.55" />
        <rect x="34" y="21" width="52" height="9" rx="2" opacity="0.55" />
        <path d="M60 34v20" />
        <path d="M52 47l8 8 8-8" />
        <path d="M30 60h60" />
        <path d="M30 60v6a2 2 0 0 0 2 2h56a2 2 0 0 0 2-2v-6" />
      </svg>
    ),
  },
];

export function FeatureTriad() {
  return (
    <section id="features" className="border-t border-rule">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-24">
        <h2 className="font-display max-w-lg text-3xl text-ink lg:text-4xl">
          Everything your books need, nothing they don&apos;t.
        </h2>

        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title} interactive className="p-6">
              <IllustrationFrame>{f.illustration}</IllustrationFrame>
              <h3 className="font-display mt-5 text-lg text-ink">{f.title}</h3>
              <p className="mt-2 text-sm text-ink-muted">{f.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

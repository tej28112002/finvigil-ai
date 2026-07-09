interface Step {
  n: number;
  title: string;
  description: string;
  icon: React.ReactNode;
}

function icon(paths: React.ReactNode) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  );
}

// A genuine 3-step sequence — Connect → Consolidate → See — so numbered
// markers (01/02/03) are honest here: order carries meaning the reader needs.
const STEPS: Step[] = [
  {
    n: 1,
    title: "Connect your brokers",
    description:
      "Link Zerodha, Angel One or Upstox with read-only access, or import a tradebook CSV. Two minutes, no passwords stored.",
    icon: icon(
      <>
        <path d="M9 17H7A5 5 0 0 1 7 7h2" />
        <path d="M15 7h2a5 5 0 1 1 0 10h-2" />
        <path d="M8 12h8" />
      </>
    ),
  },
  {
    n: 2,
    title: "We consolidate and compute",
    description:
      "Every holding is merged into one portfolio, cost basis tracked FIFO, and equity, F&O and crypto tax computed automatically.",
    icon: icon(
      <>
        <path d="M12 2 2 7l10 5 10-5-10-5Z" />
        <path d="m2 17 10 5 10-5" />
        <path d="m2 12 10 5 10-5" />
      </>
    ),
  },
  {
    n: 3,
    title: "See your complete tax picture",
    description:
      "One total value, one tax number per assessment year, and a CA-ready export — no spreadsheets, no surprises at filing time.",
    icon: icon(
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" />
        <path d="M14 2v6h6" />
        <path d="m9 16 6-6" />
        <circle cx="9.5" cy="10.5" r="0.5" fill="currentColor" />
        <circle cx="14.5" cy="15.5" r="0.5" fill="currentColor" />
      </>
    ),
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-rule bg-surface">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-24">
        <p className="text-sm font-medium uppercase tracking-wider text-brand">
          How it works
        </p>
        <h2 className="font-display mt-3 max-w-lg text-3xl text-ink lg:text-4xl">
          From scattered brokers to one number, in three steps.
        </h2>

        <div className="relative mt-14 grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-6">
          {/* Hairline connector spanning the row on md+ (behind the step markers) */}
          <div
            className="absolute left-0 right-0 top-6 hidden h-px bg-rule md:block"
            aria-hidden="true"
          />

          {STEPS.map((step) => (
            <div key={step.n} className="relative">
              <div className="flex items-center gap-4 md:block">
                {/* Numbered marker — the sequence is real, so the number earns its place */}
                <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-rule bg-bg text-brand shadow-token-sm">
                  {step.icon}
                </div>
                <span className="font-mono text-sm font-medium tabular-nums text-ink-faint md:mt-5 md:block">
                  Step {step.n}
                </span>
              </div>
              <h3 className="font-display mt-3 text-lg text-ink">{step.title}</h3>
              <p className="mt-2 text-sm text-ink-muted">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

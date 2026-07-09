interface TrustPoint {
  title: string;
  description: string;
  icon: React.ReactNode;
}

function icon(paths: React.ReactNode) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  );
}

// Each claim maps to something already shipped and true, not marketing
// copy: read-only broker sync (kite.trades() only, never places orders),
// Vault-stored per-user tokens (Supabase Vault, Phase 4.5), and the
// product's own scope boundary (never a trade-execution path anywhere).
const TRUST_POINTS: TrustPoint[] = [
  {
    title: "Read-only access",
    description:
      "We only ever read your trade history from your broker. FinVigil has no code path that places, modifies, or cancels an order.",
    icon: icon(
      <>
        <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
  {
    title: "Vault-encrypted tokens",
    description:
      "Your broker access token is encrypted at rest in a dedicated secrets vault, never stored in plain text, never shared.",
    icon: icon(
      <>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </>
    ),
  },
  {
    title: "Your money never moves",
    description:
      "There is no withdrawal, transfer, or trade-execution feature in this product — not hidden, not planned. FinVigil only shows you what's already true.",
    icon: icon(<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />),
  },
];

export function TrustSection() {
  return (
    <section className="border-t border-rule bg-surface">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-24">
        <h2 className="font-display max-w-lg text-3xl text-ink lg:text-4xl">
          FinVigil can never touch your money.
        </h2>

        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
          {TRUST_POINTS.map((t) => (
            <div key={t.title} className="border-t border-rule pt-5">
              <span className="text-brand">{t.icon}</span>
              <h3 className="font-display mt-3 text-base text-ink">{t.title}</h3>
              <p className="mt-2 text-sm text-ink-muted">{t.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

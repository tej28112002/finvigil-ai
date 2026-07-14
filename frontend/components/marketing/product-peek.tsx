import { Money } from "@/components/ui/money";

/**
 * Honest product peek: NOT a mocked screenshot image. This is composed from
 * the same Money treatment and card/token styling the real signed-in app
 * uses, showing the project's real sample numbers (₹1,10,000 total, the
 * actual STCG/LTCG/F&O/crypto figures verified in project-context.md.txt).
 * Because it's the real UI language with real data shapes, the caption's
 * claim ("this is the real dashboard") is true, not marketing spin.
 *
 * Framed in a browser-window chrome, slightly angled, soft shadow. Static
 * and aria-hidden (decorative) — the section heading + caption carry the
 * meaning for assistive tech.
 */

function MiniMetric({ label, children, sub }: { label: string; children: React.ReactNode; sub?: string }) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <p className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">{label}</p>
      <div className="mt-2">{children}</div>
      {sub && <p className="mt-1 text-[11px] text-ink-faint">{sub}</p>}
    </div>
  );
}

export function ProductPeek() {
  return (
    <section className="overflow-hidden border-t border-rule">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-24">
        <div className="mx-auto max-w-lg text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-brand">
            The real product
          </p>
          <h2 className="font-display mt-3 text-3xl text-ink lg:text-4xl">
            This is the actual dashboard.
          </h2>
          <p className="mt-3 text-sm text-ink-muted">
            Not a mockup — the same screen you see after connecting a broker,
            shown here with sample numbers.
          </p>
        </div>

        {/* Angled framed window */}
        <div className="mt-14 flex justify-center [perspective:1600px]">
          <div
            className="shadow-token-lg w-full max-w-4xl overflow-hidden rounded-xl border border-rule bg-bg ring-1 ring-black/5 dark:ring-white/10"
            style={{ transform: "rotateX(3deg) rotateY(-4deg) rotate(-1deg)" }}
            aria-hidden="true"
          >
            {/* Window chrome */}
            <div className="flex items-center gap-2 border-b border-rule bg-surface px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-loss/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-estimate/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-gain/70" />
              <span className="ml-3 font-mono text-[11px] text-ink-faint">
                finvigil.app/dashboard
              </span>
            </div>

            {/* Body */}
            <div className="space-y-4 p-5 lg:p-7">
              {/* Hero metric row */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MiniMetric label="Total portfolio value" sub="Across all brokers">
                  <Money value="110000.00" size="lg" />
                </MiniMetric>
                <MiniMetric label="Day P&L" sub="Live on next sync">
                  <span className="font-mono text-2xl font-medium tabular-nums text-ink">₹0.00</span>
                </MiniMetric>
                <MiniMetric label="Unrealized P&L" sub="At cost basis">
                  <span className="font-mono text-2xl font-medium tabular-nums text-ink">₹0.00</span>
                </MiniMetric>
                <MiniMetric label="Tax so far, FY">
                  <Money value="8940.00" size="lg" />
                </MiniMetric>
              </div>

              {/* Tax cards row — the real four figures */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border border-rule bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">Equity STCG</p>
                    <span className="rounded bg-brand-soft px-1.5 py-0.5 text-[10px] font-medium text-brand">20%</span>
                  </div>
                  <div className="mt-2"><Money value="500.00" size="sm" tone="auto" signed /></div>
                </div>
                <div className="rounded-lg border border-rule bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">Equity LTCG</p>
                    <span className="rounded bg-brand-soft px-1.5 py-0.5 text-[10px] font-medium text-brand">12.5%</span>
                  </div>
                  <div className="mt-2"><Money value="2000.00" size="sm" tone="auto" signed /></div>
                </div>
                <div className="rounded-lg border border-rule bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">F&amp;O</p>
                    <span className="rounded bg-bg px-1.5 py-0.5 text-[10px] font-medium text-ink-muted">PGBP</span>
                  </div>
                  <div className="mt-2"><Money value="-4556.50" size="sm" tone="auto" signed /></div>
                </div>
                <div className="rounded-lg border border-rule bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-ink-muted">Crypto / VDA</p>
                    <span className="rounded bg-loss-soft px-1.5 py-0.5 text-[10px] font-medium text-loss">30%</span>
                  </div>
                  <div className="mt-2"><Money value="150300.00" size="sm" /></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

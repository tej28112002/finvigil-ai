/**
 * Ledger cards: structure comes from hairline rules first, a soft base
 * shadow for gentle lift off the page. `interactive` adds a hover-lift —
 * use it for clickable/navigable cards, not for every card on a data
 * screen (BRD: data screens stay calm; drama concentrates on login/marketing).
 */
export function Card({
  children,
  className = "",
  interactive = false,
}: {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <div
      className={`shadow-token-sm rounded-md border border-rule bg-surface ${interactive ? "card-lift" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

/** A labelled metric row inside a Card — eyebrow label above the figure. */
export function MetricLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">
      {children}
    </p>
  );
}

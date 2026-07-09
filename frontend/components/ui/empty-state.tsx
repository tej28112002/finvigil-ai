/**
 * "You have a page, but no data yet" state — distinct from PagePending
 * (which is for whole pages not built yet). Used for e.g. an empty
 * portfolio, no F&O trades, no realized entries.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-rule px-6 py-14 text-center">
      {icon && (
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-brand-soft text-brand">
          {icon}
        </div>
      )}
      <p className="font-display text-lg text-ink">{title}</p>
      <p className="mt-1.5 max-w-sm text-sm text-ink-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

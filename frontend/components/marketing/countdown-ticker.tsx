/**
 * "N days left to harvest tax losses this FY" (BRD §6 Idea 4). Indian FY
 * runs April 1 – March 31; harvesting (selling a loser before year-end to
 * offset gains) only works before the FY closes. Computed server-side from
 * the real date — not a fake scarcity countdown, a real deadline every
 * Indian investor already has.
 */
function daysLeftInFY(now: Date): number {
  const fyEndYear = now.getMonth() + 1 >= 4 ? now.getFullYear() + 1 : now.getFullYear();
  const fyEnd = new Date(fyEndYear, 2, 31); // March = index 2
  const msPerDay = 1000 * 60 * 60 * 24;
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.max(0, Math.round((fyEnd.getTime() - startOfToday.getTime()) / msPerDay));
}

export function CountdownTicker() {
  const days = daysLeftInFY(new Date());

  return (
    <div className="border-b border-rule bg-estimate-soft">
      <div className="mx-auto flex max-w-7xl items-center justify-center gap-2 px-6 py-2 text-sm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-estimate" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3.5 2" />
        </svg>
        <span className="text-estimate">
          <span className="font-mono font-semibold tabular-nums">{days}</span>
          <span className="font-medium"> days left to harvest tax losses this FY</span>
        </span>
      </div>
    </div>
  );
}

/**
 * Tax Health Score (0-100) — BRD deferred-backlog widget, unlocked now that
 * Phase 7's harvesting engine exists to compute against. 100 means no
 * unharvested losses sitting in the portfolio; the score drops as more of
 * the portfolio is both (a) a larger share of open positions currently
 * showing a harvestable loss, and (b) a larger share of total portfolio
 * value tied up in that loss. This is a simple, bounded, explainable
 * heuristic — not a real financial score — deliberately built from ratios
 * already available on the dashboard, no new backend endpoint.
 *
 * BigInt paise values are converted to Number for the ratio math here: this
 * produces a derived 0-100 SCORE, not a displayed currency figure, so the
 * project's Decimal/BigInt-exact-money rule (which protects figures shown
 * to the user as money) doesn't apply — a score is inherently approximate.
 */
export function computeTaxHealthScore({
  candidateCount,
  totalOpenPositions,
  harvestableLossPaise,
  totalPortfolioPaise,
}: {
  candidateCount: number;
  totalOpenPositions: number;
  harvestableLossPaise: bigint; // magnitude (always >= 0), not signed
  totalPortfolioPaise: bigint;
}): number {
  let score = 100;

  // Up to -40: how much of the open portfolio is a harvest candidate.
  if (totalOpenPositions > 0) {
    const missedOpportunityRatio = candidateCount / totalOpenPositions;
    score -= Math.round(missedOpportunityRatio * 40);
  }

  // Up to -60: how large the harvestable loss is relative to total portfolio value.
  if (totalPortfolioPaise > 0n) {
    const lossRatio = Number(harvestableLossPaise) / Number(totalPortfolioPaise);
    score -= Math.round(Math.min(lossRatio, 1) * 60);
  }

  return Math.max(0, Math.min(100, score));
}

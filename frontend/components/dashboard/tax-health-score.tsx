import Link from "next/link";
import { Card, MetricLabel } from "@/components/ui/card";

interface Props {
  score: number;
  candidateCount: number;
}

function scoreTone(score: number): "gain" | "estimate" | "loss" {
  if (score >= 80) return "gain";
  if (score >= 50) return "estimate";
  return "loss";
}

const toneTextClass: Record<"gain" | "estimate" | "loss", string> = {
  gain: "text-gain",
  estimate: "text-estimate",
  loss: "text-loss",
};

/**
 * Tax Health Score widget (BRD deferred backlog — unlocked by Phase 7's
 * harvesting engine). See lib/harvest-score.ts for the scoring formula.
 */
export function TaxHealthScore({ score, candidateCount }: Props) {
  const tone = scoreTone(score);

  return (
    <Card className="p-5">
      <MetricLabel>Tax health score</MetricLabel>
      <div className={`mt-3 font-mono text-3xl font-semibold tabular-nums ${toneTextClass[tone]}`}>
        {score}
        <span className="text-base font-medium text-ink-faint">/100</span>
      </div>
      {candidateCount > 0 ? (
        <>
          <p className="mt-2 text-xs text-ink-faint">
            {candidateCount} position{candidateCount === 1 ? "" : "s"} sitting at an unharvested loss.
          </p>
          <Link
            href="/harvesting"
            className="mt-2 inline-block text-sm font-medium text-brand hover:text-brand-hover"
          >
            Review harvest candidates →
          </Link>
        </>
      ) : (
        <p className="mt-2 text-xs text-ink-faint">No unharvested losses right now.</p>
      )}
    </Card>
  );
}

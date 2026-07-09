"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";

interface Step {
  label: string;
  done: boolean;
  href: string;
  cta: string;
}

/**
 * Onboarding checklist (Idea 10). Steps 1-2 are computed live from real API
 * data by the caller; steps 3-4 come from localStorage flags (lib/onboarding)
 * — both are inherently frontend/session concepts with no backend endpoint
 * to check against (see Stage 2B gap #2). Disappears once all 4 are done.
 */
export function OnboardingChecklist({ steps }: { steps: Step[] }) {
  const doneCount = steps.filter((s) => s.done).length;
  if (doneCount === steps.length) return null;

  const nextStep = steps.find((s) => !s.done);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <p className="font-display text-base text-ink">Get set up</p>
        <span className="text-xs font-medium text-ink-muted">
          {doneCount} of {steps.length}
        </span>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-rule">
        <div
          className="h-full rounded-full bg-brand transition-[width] duration-300"
          style={{ width: `${(doneCount / steps.length) * 100}%` }}
        />
      </div>

      <ul className="mt-4 space-y-2">
        {steps.map((step) => (
          <li key={step.label} className="flex items-center gap-2.5 text-sm">
            <span
              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                step.done
                  ? "border-gain bg-gain-soft text-gain"
                  : "border-rule text-transparent"
              }`}
              aria-hidden="true"
            >
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <span className={step.done ? "text-ink-muted line-through" : "text-ink"}>
              {step.label}
            </span>
          </li>
        ))}
      </ul>

      {nextStep && (
        <Link
          href={nextStep.href}
          className="mt-4 inline-block text-sm font-medium text-brand hover:text-brand-hover"
        >
          {nextStep.cta} →
        </Link>
      )}
    </Card>
  );
}

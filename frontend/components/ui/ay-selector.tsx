"use client";

import Link from "next/link";
import { AY_OPTIONS } from "@/lib/ay";

// DEFAULT_AY / AY_OPTIONS live in lib/ay.ts, not here — Server Component
// pages must import them from lib/ay.ts directly (not through this file),
// since Next.js treats every export of a "use client" module as a
// client-reference stub when a Server Component imports it, even a plain
// string constant.
export function AYSelector({
  value,
  onChange,
  hrefFor,
}: {
  value: string;
  onChange?: (ay: string) => void;
  // When set, renders real <Link> pills instead of buttons. Next.js
  // prefetches the RSC payload for each visible Link automatically, so by
  // the time the user clicks a tab the server round-trip has often already
  // happened in the background — plain onClick+router.push gets none of
  // that. Use this for AY selectors that drive a Server Component page
  // (tax, crypto); keep onChange for purely client-side/local switches
  // (export page, which never navigates).
  hrefFor?: (ay: string) => string;
}) {
  return (
    <div
      role={hrefFor ? undefined : "radiogroup"}
      aria-label="Assessment year"
      className="inline-flex gap-1 rounded-md border border-rule bg-surface p-1"
    >
      {AY_OPTIONS.map((ay) => {
        const active = ay === value;
        const className = `cursor-pointer rounded px-3 py-1.5 text-sm font-medium transition-colors ${
          active ? "bg-brand text-brand-fg" : "text-ink-muted hover:text-ink"
        }`;

        if (hrefFor) {
          return (
            <Link
              key={ay}
              href={hrefFor(ay)}
              aria-current={active ? "page" : undefined}
              className={className}
            >
              AY {ay}
            </Link>
          );
        }

        return (
          <button
            key={ay}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange?.(ay)}
            className={className}
          >
            AY {ay}
          </button>
        );
      })}
    </div>
  );
}

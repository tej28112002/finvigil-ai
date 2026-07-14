"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

/**
 * Catches any thrown error from a page under (app)/ — including ApiError
 * from apiFetchServer() for real backend failures (500s, network errors,
 * unexpected 401s) that previously collapsed to null and rendered as a
 * misleading empty state. This boundary sits inside (app)/layout.tsx, so
 * the sidebar/header stay mounted; only the content area is replaced.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex justify-center pt-10">
      <Card className="w-full max-w-md p-8 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-md bg-loss-soft text-loss">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
            <path d="M12 9v4" />
            <circle cx="12" cy="17" r="0.5" fill="currentColor" />
          </svg>
        </div>
        <h2 className="font-display mt-4 text-xl text-ink">Something went wrong</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          We couldn&apos;t load this page. This is usually temporary — try
          again in a moment.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button onClick={reset}>Try again</Button>
          <a
            href="/dashboard"
            className="inline-flex h-9 items-center rounded-md border border-rule px-4 text-sm font-medium text-ink transition-colors hover:border-rule-strong"
          >
            Back to dashboard
          </a>
        </div>
      </Card>
    </div>
  );
}

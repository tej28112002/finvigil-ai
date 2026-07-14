"use client";

import { useEffect } from "react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

/**
 * Root error boundary — catches thrown errors on the marketing homepage,
 * login, or anywhere outside the authenticated (app)/ shell (which has its
 * own error.tsx). No sidebar/header exists at this level, so this brings
 * its own full-viewport frame.
 */
export default function RootError({
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6">
      <Logo markSize={24} wordmarkClassName="text-xl text-ink" className="mb-8" />
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
          This is usually temporary — try again in a moment.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button onClick={reset}>Try again</Button>
          <a
            href="/"
            className="inline-flex h-9 items-center rounded-md border border-rule px-4 text-sm font-medium text-ink transition-colors hover:border-rule-strong"
          >
            Back home
          </a>
        </div>
      </Card>
    </div>
  );
}

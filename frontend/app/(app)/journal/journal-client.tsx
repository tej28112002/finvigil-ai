"use client";

import { BrokerActionsBar } from "@/components/shared/broker-actions-bar";

export function JournalClient() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">AI Journaling</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your trading performance, automatically computed from your trade history.
        </p>
      </div>

      <BrokerActionsBar />

      <div
        style={{ textAlign: "center", padding: "60px 20px" }}
        className="text-ink-muted"
      >
        AI trade analysis will appear here after you connect your broker or
        upload your tradebook.
      </div>
    </div>
  );
}

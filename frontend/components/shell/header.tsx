"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { findNavItem } from "@/components/shell/nav-config";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface BrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}

interface BrokerSyncResult {
  success: boolean;
  holdings_synced: number;
  trades_imported: number;
  error?: string | null;
}

// Groww is skipped here -- its TOTP flow doesn't have the same "connected
// but silently importing nothing" failure mode this button exists to fix.
const SYNCABLE_BROKERS = ["zerodha", "upstox"];
const BROKER_LABELS: Record<string, string> = { zerodha: "Zerodha", upstox: "Upstox" };

export function Header({ onOpenMenu }: { onOpenMenu: () => void }) {
  const pathname = usePathname();
  const title = findNavItem(pathname)?.label ?? "FinVigil";
  const [syncing, setSyncing] = useState(false);
  const [syncNote, setSyncNote] = useState<string | null>(null);

  async function handleSyncClick() {
    setSyncing(true);
    setSyncNote("Checking connected brokers…");
    try {
      const brokers = await apiFetch<BrokerConnection[]>("/brokers/");
      const active = brokers.filter(
        (b) => b.status === "active" && SYNCABLE_BROKERS.includes(b.broker_name)
      );
      if (active.length === 0) {
        setSyncNote("No connected brokers to sync — visit the Brokers page to connect one.");
        return;
      }

      const parts: string[] = [];
      for (const broker of active) {
        const label = BROKER_LABELS[broker.broker_name] ?? broker.broker_name;
        setSyncNote([...parts, `Syncing ${label}…`].join(" · "));
        try {
          await apiFetch<BrokerSyncResult>(
            `/brokers/${broker.broker_name}/sync?broker_connection_id=${broker.id}`,
            { method: "POST" }
          );
          parts.push(`Syncing ${label}... done`);
        } catch {
          parts.push(`Syncing ${label}... failed`);
        }
        setSyncNote(parts.join(" · "));
      }
    } catch {
      setSyncNote("Could not load brokers — try the Brokers page directly.");
    } finally {
      setSyncing(false);
      window.setTimeout(() => setSyncNote(null), 6000);
    }
  }

  return (
    <header className="glass theme-transition sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-rule px-4 md:px-6">
      {/* Mobile menu */}
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Open navigation"
        className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md border border-rule text-ink-muted hover:text-ink lg:hidden"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>

      <h1 className="font-display text-lg text-ink">{title}</h1>

      <div className="ml-auto flex items-center gap-2">
        {syncNote && (
          <span
            role="status"
            className="hidden max-w-xs truncate text-xs text-ink-muted sm:inline"
          >
            {syncNote}
          </span>
        )}
        <Button variant="secondary" onClick={handleSyncClick} loading={syncing} className="h-9">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <path d="M21 3v6h-6" />
          </svg>
          <span className="hidden sm:inline">Sync all brokers</span>
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}

"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { findNavItem } from "@/components/shell/nav-config";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

export function Header({ onOpenMenu }: { onOpenMenu: () => void }) {
  const pathname = usePathname();
  const title = findNavItem(pathname)?.label ?? "FinVigil";
  const [syncNote, setSyncNote] = useState(false);

  /* "Sync all brokers" is present per BRD §7; its real wiring (broker
     lookup → per-broker sync → result feedback) lands with the Brokers
     page in Stage 2B. Until then the click is honest about that. */
  function handleSyncClick() {
    setSyncNote(true);
    window.setTimeout(() => setSyncNote(false), 3500);
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
            className="hidden text-xs text-ink-muted sm:inline"
          >
            Broker sync arrives with the Brokers page.
          </span>
        )}
        <Button variant="secondary" onClick={handleSyncClick} className="h-9">
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

"use client";

import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

/** Marketing top nav (BRD §6.1). Pricing/About are honest placeholders —
 * muted and non-navigating, same "soon" convention as the app sidebar,
 * never a dead link dressed up as a real page. */
export function MarketingNav() {
  return (
    <header className="glass theme-transition sticky top-0 z-30 border-b border-rule">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Logo markSize={24} wordmarkClassName="text-xl" />

        <nav className="hidden items-center gap-7 md:flex" aria-label="Marketing">
          <a href="#features" className="text-sm font-medium text-ink-muted transition-colors hover:text-ink">
            Features
          </a>
          <span className="flex items-center gap-1.5 text-sm font-medium text-ink-faint">
            Pricing
            <span className="rounded border border-rule px-1 py-px text-[9px] uppercase tracking-wide">Soon</span>
          </span>
          <span className="flex items-center gap-1.5 text-sm font-medium text-ink-faint">
            About
            <span className="rounded border border-rule px-1 py-px text-[9px] uppercase tracking-wide">Soon</span>
          </span>
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="hidden sm:block">
            <Button variant="ghost">Log in</Button>
          </Link>
          <Link href="/login">
            <Button variant="primary">Get started</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}

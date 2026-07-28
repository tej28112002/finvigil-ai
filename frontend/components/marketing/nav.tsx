"use client";

import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

/** Marketing top nav (BRD §6.1). */
export function MarketingNav() {
  return (
    <header className="glass theme-transition sticky top-0 z-30 border-b border-rule">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Logo markSize={22} wordmarkClassName="text-lg sm:text-xl" />

        <nav className="hidden items-center gap-7 md:flex" aria-label="Marketing">
          <a href="#features" className="text-sm font-medium text-ink-muted transition-colors hover:text-ink">
            Features
          </a>
          <Link href="/pricing" className="text-sm font-medium text-ink-muted transition-colors hover:text-ink">
            Pricing
          </Link>
          <Link href="/about" className="text-sm font-medium text-ink-muted transition-colors hover:text-ink">
            About
          </Link>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          <Link href="/login" className="hidden sm:block">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/login?mode=signup">
            <Button variant="primary" className="px-3 sm:px-4">
              Get started
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}

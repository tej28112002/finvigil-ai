"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

/** Marketing top nav (BRD §6.1). */
export function MarketingNav() {
  const pathname = usePathname();
  const router = useRouter();

  // href="/#features" alone would still work from /pricing or /about (it's
  // an absolute path, not a bare #anchor), but a plain link re-navigates
  // the whole page even when already on "/" — this handler skips that and
  // just scrolls when we're already home, matching how a same-page anchor
  // should feel.
  function handleFeaturesClick(e: React.MouseEvent<HTMLAnchorElement>) {
    if (pathname === "/") {
      e.preventDefault();
      document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
    } else {
      e.preventDefault();
      router.push("/#features");
    }
  }

  return (
    <header className="glass theme-transition sticky top-0 z-30 border-b border-rule">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Logo markSize={22} wordmarkClassName="text-lg sm:text-xl" />

        <nav className="hidden items-center gap-7 md:flex" aria-label="Marketing">
          <Link
            href="/#features"
            onClick={handleFeaturesClick}
            className="text-sm font-medium text-ink-muted transition-colors hover:text-ink"
          >
            Features
          </Link>
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

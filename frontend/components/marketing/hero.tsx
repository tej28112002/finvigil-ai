import Link from "next/link";
import { AnimatedOneNumber } from "@/components/marketing/animated-one-number";
import { Button } from "@/components/ui/button";

/**
 * BRD §6.3 — "the place for visual drama." Headline + CTAs on the left, the
 * animated "One Number" hero on the right (three brokers converging into one
 * counted-up total). The homepage uses AnimatedOneNumber; the login page
 * keeps the static FloatingCardsScene — deliberately two different visuals
 * for two different contexts.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Restrained dot-grid ambience on the page bg. */}
      <div
        className="pointer-events-none absolute inset-0 text-ink opacity-[0.03]"
        style={{
          backgroundImage: "radial-gradient(currentColor 1.2px, transparent 1.2px)",
          backgroundSize: "26px 26px",
        }}
        aria-hidden="true"
      />

      <div className="relative mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-2 lg:items-center lg:py-28">
        <div>
          <p className="text-sm font-medium text-ink-faint">
            Portfolio intelligence &amp; tax clarity for Indian investors
          </p>
          <h1 className="font-display mt-4 text-4xl leading-[1.08] text-ink sm:text-5xl lg:text-6xl">
            All your brokers.
            <br />
            One picture.
            <br />
            <span className="italic text-brand">Zero tax surprises.</span>
          </h1>
          <p className="mt-6 max-w-md text-base text-ink-muted">
            Connect Zerodha, Upstox, Groww and more. FinVigil consolidates
            every holding, runs the FIFO cost basis, and computes your equity,
            F&amp;O and crypto tax — read-only, always.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/login?mode=signup">
              <Button variant="primary" className="h-11 px-6 text-base">
                Get started
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button variant="secondary" className="h-11 px-6 text-base">
                How it works
              </Button>
            </a>
          </div>
        </div>

        <AnimatedOneNumber />
      </div>
    </section>
  );
}

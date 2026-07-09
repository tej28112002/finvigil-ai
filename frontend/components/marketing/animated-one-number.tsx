"use client";

import { useEffect, useState } from "react";

/**
 * "One Number" hero visual (BRD §6.3, Idea 1+3). Three broker chips fly in
 * staggered, then a central brand panel scales in and its total counts up
 * from ₹0 to the consolidated value while the est-tax figure ticks up
 * alongside. CSS transitions for reveal + a single requestAnimationFrame
 * loop for the count-up — no animation library.
 *
 * Fires on every mount (page load / reload), per product choice — not gated
 * behind a "seen once" flag. prefers-reduced-motion short-circuits the whole
 * thing: final values render immediately, no rAF, no transitions.
 *
 * Distinct from the login page's FloatingCardsScene (which stays as-is) —
 * that one is a static illustration; this one is the animated marketing hero.
 */

const BROKERS = [
  { name: "Zerodha", value: 820400, dot: "var(--color-broker-zerodha)" },
  { name: "Angel One", value: 410600, dot: "var(--color-broker-angelone)" },
  { name: "Upstox", value: 221300, dot: "var(--color-broker-upstox)" },
];
const TOTAL = 1452300;
const EST_TAX = 8940;
const COUNT_MS = 1400;

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

// ease-out cubic — decisive start, gentle settle (trust-appropriate motion)
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

export function AnimatedOneNumber() {
  // count = 0..1 progress; chipsIn triggers the staggered chip reveal;
  // panelIn triggers the central card scale-in.
  const [progress, setProgress] = useState(0);
  const [chipsIn, setChipsIn] = useState(false);
  const [panelIn, setPanelIn] = useState(false);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduced) {
      // Skip all motion — show the finished state at once.
      setChipsIn(true);
      setPanelIn(true);
      setProgress(1);
      return;
    }

    // Chips reveal immediately (their own CSS transition-delays stagger them),
    // central panel a beat later, then the number counts up.
    const chipTimer = window.setTimeout(() => setChipsIn(true), 60);
    const panelTimer = window.setTimeout(() => setPanelIn(true), 700);

    let raf = 0;
    let start = 0;
    const countTimer = window.setTimeout(() => {
      const tick = (now: number) => {
        if (!start) start = now;
        const t = Math.min(1, (now - start) / COUNT_MS);
        setProgress(easeOutCubic(t));
        if (t < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    }, 950);

    return () => {
      window.clearTimeout(chipTimer);
      window.clearTimeout(panelTimer);
      window.clearTimeout(countTimer);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  const total = Math.round(TOTAL * progress);
  const estTax = Math.round(EST_TAX * progress);

  return (
    <div className="relative min-h-[380px] lg:min-h-[440px]" aria-hidden="true">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[380px] w-[380px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand opacity-[0.10] blur-3xl" />

      <div className="relative flex h-full min-h-[380px] flex-col items-center justify-center gap-4 lg:min-h-[440px]">
        {/* Broker chips row — staggered fly-in */}
        <div className="flex flex-wrap items-center justify-center gap-2.5">
          {BROKERS.map((b, i) => (
            <div
              key={b.name}
              className={[
                "flex items-center gap-2.5 rounded-lg border border-rule bg-surface px-3.5 py-2 shadow-token-sm",
                "transition-all duration-500 ease-out",
                chipsIn ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0",
              ].join(" ")}
              style={{ transitionDelay: chipsIn ? `${i * 250}ms` : "0ms" }}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: b.dot }}
              />
              <span className="whitespace-nowrap text-sm font-medium text-ink">
                {b.name}
              </span>
              <span className="whitespace-nowrap font-mono text-sm font-medium tabular-nums text-ink-muted">
                ₹{inr.format(b.value)}
              </span>
            </div>
          ))}
        </div>

        {/* Converging connector — three faint lines pointing down to the total */}
        <svg
          width="220"
          height="34"
          viewBox="0 0 220 34"
          fill="none"
          className={`text-rule-strong transition-opacity duration-500 ${
            panelIn ? "opacity-60" : "opacity-0"
          }`}
        >
          <path d="M40 2 Q110 20 110 32" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M110 2 L110 32" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M180 2 Q110 20 110 32" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>

        {/* Central total — brand panel, scales in, number counts up */}
        <div
          className={[
            "shadow-token-lg rounded-2xl bg-brand px-8 py-6 text-brand-fg",
            "transition-all duration-700 ease-out",
            panelIn ? "scale-100 opacity-100" : "scale-95 opacity-0",
          ].join(" ")}
        >
          <p className="text-[11px] font-medium uppercase tracking-wider opacity-75">
            Total portfolio value
          </p>
          <p className="mt-1.5 whitespace-nowrap font-mono text-4xl font-semibold tabular-nums tracking-tight lg:text-5xl">
            ₹{inr.format(total)}
          </p>
          <div className="mt-3 flex items-center gap-2 border-t border-brand-fg/20 pt-3">
            <span className="text-[11px] font-medium uppercase tracking-wide opacity-75">
              Est. tax AY 26-27
            </span>
            <span className="whitespace-nowrap font-mono text-sm font-semibold tabular-nums">
              ₹{inr.format(estTax)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

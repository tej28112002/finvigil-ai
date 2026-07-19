"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

const QUICK_NAV = [
  {
    title: "AI Journaling",
    desc: "Record trade notes and import your tradebook",
    href: "/journal",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="9" y="2" width="6" height="12" rx="3" />
        <path d="M5 10a7 7 0 0 0 14 0" />
        <path d="M12 19v3" />
      </svg>
    ),
  },
  {
    title: "Cross Broker Portfolio",
    desc: "Invested amount, P&L, XIRR and holdings across all brokers",
    href: "/portfolio",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 2 2 7l10 5 10-5-10-5Z" />
        <path d="m2 17 10 5 10-5" />
        <path d="m2 12 10 5 10-5" />
      </svg>
    ),
  },
  {
    title: "Tax Harvesting",
    desc: "Find tax-loss opportunities before year end",
    href: "/harvesting",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
        <path d="M2 21c0-3 1.85-5.36 5.08-6" />
      </svg>
    ),
  },
  {
    title: "Portfolio Backtesting",
    desc: "Replay your trades and run Monte Carlo simulations",
    href: "/replay",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 12a9 9 0 1 0 9-9" />
        <path d="M3 4v5h5" />
        <path d="M12 8v4l3 2" />
      </svg>
    ),
  },
  {
    title: "CA Export",
    desc: "Download your ITR-3 bundle for your chartered accountant",
    href: "/export",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </svg>
    ),
  },
];

export function WelcomeScreen({
  userId,
  firstName,
}: {
  userId: string;
  firstName: string;
}) {
  // localStorage is unavailable during SSR. Default null so we don't render
  // the greeting on the server (no hydration mismatch), then pick up the
  // real first-vs-return state after mount.
  const [isFirstVisit, setIsFirstVisit] = useState<boolean | null>(null);

  useEffect(() => {
    if (!userId) return;
    const key = `finvigil_seen_${userId}`;
    const seen = !!localStorage.getItem(key);
    setIsFirstVisit(!seen);
    if (!seen) {
      localStorage.setItem(key, "1");
    }
  }, [userId]);

  const greeting =
    isFirstVisit === null
      ? `Hello, ${firstName}!`
      : isFirstVisit
        ? `Welcome, ${firstName}!`
        : `Welcome back, ${firstName}!`;

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      {/* Greeting */}
      <div>
        <h1 className="font-display text-4xl font-bold text-ink">{greeting}</h1>
        <p className="mt-2 text-base text-ink-muted">
          Your portfolio intelligence platform for smarter tax and investment decisions.
        </p>
      </div>

      {/* Quick-nav cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {QUICK_NAV.map((card) => (
          <Link key={card.href} href={card.href} className="group block">
            <Card
              interactive
              className="flex h-full flex-col gap-3 p-5 transition-shadow"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-soft text-brand">
                {card.icon}
              </div>
              <div>
                <p className="font-medium text-ink">{card.title}</p>
                <p className="mt-1 text-sm text-ink-muted">{card.desc}</p>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

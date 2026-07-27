"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";

interface FeatureCard {
  title: string;
  whatItDoes: string;
  steps: string[];
  cta: string;
  href: string;
  icon: React.ReactNode;
  wide?: boolean;
}

const QUICK_NAV: FeatureCard[] = [
  {
    title: "AI Journaling",
    whatItDoes:
      "Track your trading performance with automatic analytics. Get win rate, profit factor, Sharpe ratio, and equity curve — all computed from your real trade history. Voice and text note-taking included.",
    steps: [
      "Connect your broker or upload a CSV tradebook",
      "Your trading metrics compute automatically",
      "Add voice/text notes after each trade session",
      "Track your consistency over time",
    ],
    cta: "Open AI Journaling →",
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
    whatItDoes:
      "See your complete portfolio across all brokers in one place. Invested amount, current value, P&L, XIRR, Alpha vs Nifty 50, Beta, and risk metrics — all in one view.",
    steps: [
      "Connect Zerodha, Upstox, or Groww (or upload CSV)",
      'Click "Sync all brokers" to fetch latest holdings',
      "View consolidated metrics across all accounts",
      "Monitor XIRR and Alpha vs Nifty to track real performance",
    ],
    cta: "View Portfolio →",
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
    title: "Tax Harvesting Intelligence",
    whatItDoes:
      "Get personalised AI recommendations to legally reduce your capital gains tax. Strategies include LTCG exemption harvesting, holding period optimisation, and tax loss harvesting — all based on Indian tax law.",
    steps: [
      "Ensure your trades are synced (broker or CSV)",
      "Visit Tax Harvesting to see your FY tax position",
      "Review each recommended strategy",
      "Implement strategies through your broker before March 31",
    ],
    cta: "View Tax Strategies →",
    href: "/harvesting",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
        <path d="M2 21c0-3 1.85-5.36 5.08-6" />
      </svg>
    ),
  },
  {
    title: "Strategy Backtester",
    whatItDoes:
      "Build and test options strategies against historical data. Configure instruments, entry/exit rules, leg builder with up to 10 legs, stop loss, targets, and trailing options — then see year-wise results.",
    steps: [
      "Go to Strategy Backtester",
      "Select instrument (NIFTY, BANKNIFTY, etc.)",
      "Build your strategy using the Leg Builder",
      "Set the date range and click Run Backtest",
    ],
    cta: "Open Backtester →",
    href: "/backtest",
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
    whatItDoes:
      "Download your complete tax package for your Chartered Accountant. Includes ITR-3 schedules (JSON), realized gains CSV, holdings CSV, and a README — everything your CA needs for filing.",
    steps: [
      "Ensure your trades are synced",
      "Go to CA Export",
      "Download the ZIP bundle",
      "Hand the ZIP to your CA for ITR-3 filing",
    ],
    cta: "Download CA Bundle →",
    href: "/export",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </svg>
    ),
    wide: true,
  },
];

function FeatureGuideCard({ card }: { card: FeatureCard }) {
  return (
    <Card className={`flex h-full flex-col p-5 ${card.wide ? "md:col-span-2" : ""}`}>
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-soft text-brand">
        {card.icon}
      </div>
      <p className="mt-3 text-base font-semibold text-ink">{card.title}</p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink-muted">{card.whatItDoes}</p>

      <hr className="my-4 border-rule" />

      <MetricLabel>How to get started</MetricLabel>
      <ol className="mt-2 space-y-1.5 text-[13px] text-ink-muted">
        {card.steps.map((step, i) => (
          <li key={i} className="flex gap-2">
            <span className="shrink-0 font-mono text-ink-faint">{i + 1}.</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>

      <div className="mt-4 flex-1" />

      <Link href={card.href} className="mt-4 block">
        <Button className="w-full justify-center">{card.cta}</Button>
      </Link>
    </Card>
  );
}

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

      {/* Feature guide cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {QUICK_NAV.map((card) => (
          <FeatureGuideCard key={card.href} card={card} />
        ))}
      </div>
    </div>
  );
}

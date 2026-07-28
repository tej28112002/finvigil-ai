"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { IconTile } from "@/components/ui/icon-tile";
import { Money } from "@/components/ui/money";
import { apiFetch } from "@/lib/api";
import { parseDecimalToPaise, sumToPaise } from "@/lib/format";

// "gain" is a special case handled outside IconTile (see FeatureGuideCard)
// — reuses the P&L-reserved --gain token for this one card per an explicit
// request, rather than extending IconTile's own color set.
type FeatureCardColor = "orange" | "blue" | "purple" | "gain";

interface FeatureCard {
  title: string;
  whatItDoes: string;
  steps: string[];
  cta: string;
  href: string;
  icon: React.ReactNode;
  color: FeatureCardColor;
  wide?: boolean;
}

const QUICK_NAV: FeatureCard[] = [
  {
    title: "AI Journaling",
    color: "orange",
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
    color: "blue",
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
    color: "gain",
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
    color: "purple",
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
    color: "orange",
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
      {card.color === "gain" ? (
        // Reuses the P&L-reserved --gain token for this one card (Tax
        // Harvesting) rather than extending IconTile's own color set,
        // which stays untouched.
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-gain-soft text-gain">
          {card.icon}
        </div>
      ) : (
        <IconTile color={card.color} size={9}>
          {card.icon}
        </IconTile>
      )}
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

// ── Connected-state overview ────────────────────────────────────────────
// Shown above the feature guide cards once the user actually has synced
// portfolio data. XIRR/beta/volatility are fetched client-side (same split
// portfolio-client.tsx already uses) so the DB-backed hero cards render
// immediately and only the yfinance-backed risk metrics show a skeleton.

interface DashboardPortfolioItem {
  instrument_id: string;
  total_invested: string;
}
interface DashboardBrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}
interface XirrSnapshot {
  xirr_percent: number | null;
  beta: number | null;
  volatility_percent: number | null;
}

const BROKER_LABELS: Record<string, string> = {
  zerodha: "Zerodha",
  upstox: "Upstox",
  groww: "Groww",
  wazirx: "WazirX",
  coindcx: "CoinDCX",
  csv: "CSV Import",
};

function numStr(v: number | null | undefined, digits = 2, suffix = ""): string {
  if (v === null || v === undefined) return "—";
  const prefix = suffix === "%" && v > 0 ? "+" : "";
  return `${prefix}${v.toFixed(digits)}${suffix}`;
}

function pctColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-ink-faint";
  if (v > 0) return "text-gain";
  if (v < 0) return "text-loss";
  return "text-ink";
}

function StatSkeleton() {
  return <div className="h-8 w-20 animate-pulse rounded bg-rule" />;
}

function ConnectedOverview({
  portfolio,
  brokers,
  totalEquityValue,
}: {
  portfolio: DashboardPortfolioItem[];
  brokers: DashboardBrokerConnection[];
  totalEquityValue: string | null;
}) {
  const [xirr, setXirr] = useState<XirrSnapshot | null>(null);
  const [xirrLoading, setXirrLoading] = useState(true);

  useEffect(() => {
    apiFetch<XirrSnapshot>("/portfolio/xirr")
      .then(setXirr)
      .catch(() => setXirr(null))
      .finally(() => setXirrLoading(false));
  }, []);

  const investedPaise = sumToPaise(portfolio.map((p) => p.total_invested));
  const currentPaise = totalEquityValue ? parseDecimalToPaise(totalEquityValue) : null;
  const pnlPaise = currentPaise !== null ? currentPaise - investedPaise : null;
  const activeBrokers = brokers.filter((b) => b.status === "active");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Hero — Portfolio Value, the signature element: a soft glow in the
            current theme's brand color, echoing the marketing homepage's
            "one number" motif now that it's showing the user's real number. */}
        <Card className="relative overflow-hidden p-6 lg:col-span-2">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.08]"
            style={{
              background: "radial-gradient(circle at 12% 10%, var(--brand), transparent 60%)",
            }}
            aria-hidden="true"
          />
          <div className="relative flex items-start gap-4">
            <IconTile color="brand" size={10}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 2 2 7l10 5 10-5-10-5Z" />
                <path d="m2 17 10 5 10-5" />
                <path d="m2 12 10 5 10-5" />
              </svg>
            </IconTile>
            <div>
              <MetricLabel>Portfolio Value</MetricLabel>
              <div className="mt-2">
                {currentPaise !== null ? (
                  <Money value={currentPaise} size="xl" />
                ) : (
                  <span className="font-mono text-4xl font-medium text-ink-faint">—</span>
                )}
              </div>
              <p className="mt-1.5 text-xs text-ink-faint">Across all connected brokers</p>
            </div>
          </div>
        </Card>

        {/* Risk snapshot */}
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <IconTile color="purple">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
              </svg>
            </IconTile>
            <MetricLabel>Risk Snapshot</MetricLabel>
          </div>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-ink-muted">Beta vs Nifty 50</span>
              {xirrLoading ? (
                <div className="h-4 w-10 animate-pulse rounded bg-rule" />
              ) : (
                <span className="font-mono text-sm font-medium text-ink">{numStr(xirr?.beta)}</span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-ink-muted">Volatility</span>
              {xirrLoading ? (
                <div className="h-4 w-10 animate-pulse rounded bg-rule" />
              ) : (
                <span className="font-mono text-sm font-medium text-ink">
                  {numStr(xirr?.volatility_percent, 1, "%")}
                </span>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Stat tiles — each a different accent color, the "purple/gray/blue"
          card variety on top of the site's brand color. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <IconTile color="orange" size={8}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 3v12" />
                <path d="m7 10 5 5 5-5" />
                <path d="M5 19h14" />
              </svg>
            </IconTile>
            <MetricLabel>Invested</MetricLabel>
          </div>
          <div className="mt-3">
            <Money value={investedPaise} size="lg" />
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <IconTile color="blue" size={8}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 17l6-6 4 4 8-8" />
                <path d="M15 7h6v6" />
              </svg>
            </IconTile>
            <MetricLabel>Profit / Loss</MetricLabel>
          </div>
          <div className="mt-3">
            {pnlPaise !== null ? (
              <Money value={pnlPaise} size="lg" tone="auto" signed />
            ) : (
              <span className="font-mono text-2xl font-medium text-ink-faint">—</span>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <IconTile color="purple" size={8}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="7" cy="7" r="2" />
                <circle cx="17" cy="17" r="2" />
                <path d="M17 7 7 17" />
              </svg>
            </IconTile>
            <MetricLabel>XIRR</MetricLabel>
          </div>
          <div className="mt-3">
            {xirrLoading ? (
              <StatSkeleton />
            ) : (
              <span className={`font-mono text-2xl font-medium ${pctColor(xirr?.xirr_percent)}`}>
                {numStr(xirr?.xirr_percent, 2, "%")}
              </span>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <IconTile color="neutral" size={8}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 17H7A5 5 0 0 1 7 7h2" />
                <path d="M15 7h2a5 5 0 1 1 0 10h-2" />
                <path d="M8 12h8" />
              </svg>
            </IconTile>
            <MetricLabel>Brokers Connected</MetricLabel>
          </div>
          <div className="mt-3 font-mono text-2xl font-medium text-ink">{activeBrokers.length}</div>
        </Card>
      </div>

      {activeBrokers.length > 0 && (
        <Card className="p-5">
          <MetricLabel>Connected brokers</MetricLabel>
          <div className="mt-3 flex flex-wrap gap-2">
            {activeBrokers.map((b) => (
              <span
                key={b.id}
                className="inline-flex items-center gap-1.5 rounded-full border border-rule px-3 py-1.5 text-sm font-medium text-ink"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-gain" aria-hidden="true" />
                {BROKER_LABELS[b.broker_name] ?? b.broker_name}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export function DashboardHome({
  userId,
  firstName,
  hasData,
  portfolio,
  brokers,
  totalEquityValue,
}: {
  userId: string;
  firstName: string;
  hasData: boolean;
  portfolio: DashboardPortfolioItem[];
  brokers: DashboardBrokerConnection[];
  totalEquityValue: string | null;
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
      {/* 1 — Greeting, always shown */}
      <div>
        <h1 className="font-display text-4xl font-bold text-ink">{greeting}</h1>
        <p className="mt-2 text-base text-ink-muted">
          Your portfolio intelligence platform for smarter tax and investment decisions.
        </p>
      </div>

      {/* 2 — Connected-state stats overview, only once the user has data */}
      {hasData && (
        <ConnectedOverview
          portfolio={portfolio}
          brokers={brokers}
          totalEquityValue={totalEquityValue}
        />
      )}

      {/* 3 — Feature guide cards, always shown: both new and existing
          users benefit from knowing what each feature does and how to
          use it, not just users who haven't connected anything yet. */}
      <div>
        {hasData && (
          <h2 className="font-display mb-4 text-lg text-ink">Explore FinVigil</h2>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {QUICK_NAV.map((card) => (
            <FeatureGuideCard key={card.href} card={card} />
          ))}
        </div>
      </div>
    </div>
  );
}

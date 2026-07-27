export interface PricingPlan {
  name: string;
  price: string;
  cadence: string;
  equivalentMonthly?: string;
  savings?: string;
  badge?: string;
  features: string[];
  featured?: boolean;
}

export const PRICING_PLANS: PricingPlan[] = [
  {
    name: "Free",
    price: "₹0",
    cadence: "/month",
    features: [
      "Connect 1 broker",
      "Basic portfolio view",
      "FIFO cost basis",
      "Basic tax summary",
      "Up to 50 trades/month",
      "CSV import",
    ],
  },
  {
    name: "Pro Monthly",
    price: "₹299",
    cadence: "/month",
    features: [
      "Everything in Free",
      "Unlimited brokers",
      "Full STCG/LTCG tax engine",
      "F&O and crypto tax",
      "AIS reconciliation",
      "Tax-loss harvesting",
      "CA Export ZIP bundle",
      "ITR-3 schedule export",
      "Monte Carlo simulation",
      "Portfolio replay engine",
      "Priority email support",
    ],
  },
  {
    name: "Pro Annual",
    price: "₹2,499",
    cadence: "/year",
    equivalentMonthly: "₹208/month",
    savings: "Save ₹1,089",
    badge: "Most Popular",
    featured: true,
    features: ["Everything in Pro Monthly"],
  },
  {
    name: "Premium Monthly",
    price: "₹799",
    cadence: "/month",
    features: [
      "Everything in Pro",
      "Voice trading journal",
      "Advanced Monte Carlo",
      "Dedicated CA support",
      "White-glove onboarding",
    ],
  },
  {
    name: "Premium Annual",
    price: "₹6,999",
    cadence: "/year",
    equivalentMonthly: "₹583/month",
    savings: "Save ₹2,589",
    badge: "Best Value",
    featured: true,
    features: ["Everything in Premium Monthly"],
  },
];

export interface ComparisonRow {
  feature: string;
  free: string;
  pro: string;
  premium: string;
}

export const COMPARISON_ROWS: ComparisonRow[] = [
  { feature: "Brokers", free: "1", pro: "∞", premium: "∞" },
  { feature: "Trades/month", free: "50", pro: "∞", premium: "∞" },
  { feature: "Tax engine", free: "Basic", pro: "Full", premium: "Full" },
  { feature: "AIS reconciliation", free: "✗", pro: "✓", premium: "✓" },
  { feature: "Tax-loss harvesting", free: "✗", pro: "✓", premium: "✓" },
  { feature: "CA Export", free: "✗", pro: "✓", premium: "✓" },
  { feature: "ITR-3 Export", free: "✗", pro: "✓", premium: "✓" },
  { feature: "Monte Carlo", free: "✗", pro: "✓", premium: "✓" },
  { feature: "Voice Journal", free: "✗", pro: "✗", premium: "✓" },
  { feature: "CA Support", free: "✗", pro: "✗", premium: "✓" },
];

export interface FaqItem {
  question: string;
  answer: string;
}

export const PRICING_FAQS: FaqItem[] = [
  {
    question: "Is my data safe?",
    answer:
      "Yes. FinVigil is read-only — there is no code path anywhere in the product that places, modifies, or cancels a trade. Broker access tokens are encrypted at rest in a dedicated secrets vault, never stored in plain text, and all data is hosted in Supabase's Mumbai (ap-south-1) region for DPDP compliance.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. You can cancel your subscription at any time from the Billing page — you'll keep Pro/Premium access until the end of your current billing period, and you're never locked into a contract.",
  },
  {
    question: "Which brokers do you support?",
    answer:
      "Zerodha, Upstox, and Groww via read-only OAuth (more brokers coming soon), plus WazirX and CoinDCX for crypto. You can also import any broker's tradebook via CSV if a direct connection isn't available yet.",
  },
  {
    question: "What is AIS reconciliation?",
    answer:
      "AIS (Annual Information Statement) is the tax data the Income Tax Department already has on file for you. FinVigil compares your AIS against what it computed from your actual trades and flags mismatches — missing entries, quantity or price differences, duplicates — before you file, so nothing catches you off guard later.",
  },
  {
    question: "Do I need a CA to use FinVigil?",
    answer:
      "No — Free and Pro plans work standalone for your own tax clarity. But FinVigil isn't a tax preparer or filer: it produces capital-gains figures and CA-ready exports, and your CA (or you) still handles the actual ITR filing. Premium includes dedicated CA support if you want that extra layer.",
  },
];

/**
 * Sidebar navigation structure (BRD §7 — approved mockup).
 * "soon" items render with a muted Coming-soon tag; their pages are
 * designed empty states, never dead links.
 */

export interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  soon?: boolean;
  /** One-liner used by the page-level empty state. */
  description: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

function icon(paths: React.ReactNode) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths}
    </svg>
  );
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      {
        label: "Dashboard",
        href: "/dashboard",
        description: "Your whole portfolio in one picture.",
        icon: icon(
          <>
            <rect x="3" y="3" width="7" height="9" rx="1" />
            <rect x="14" y="3" width="7" height="5" rx="1" />
            <rect x="14" y="12" width="7" height="9" rx="1" />
            <rect x="3" y="16" width="7" height="5" rx="1" />
          </>
        ),
      },
      {
        label: "Portfolio",
        href: "/portfolio",
        description: "Every open lot, FIFO cost basis, per instrument.",
        icon: icon(
          <>
            <path d="M12 2 2 7l10 5 10-5-10-5Z" />
            <path d="m2 17 10 5 10-5" />
            <path d="m2 12 10 5 10-5" />
          </>
        ),
      },
      {
        label: "Tax summary",
        href: "/tax",
        description: "STCG, LTCG, F&O and crypto — one tax picture.",
        icon: icon(
          <>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" />
            <path d="M14 2v6h6" />
            <path d="m9 16 6-6" />
            <circle cx="9.5" cy="10.5" r="0.5" fill="currentColor" />
            <circle cx="14.5" cy="15.5" r="0.5" fill="currentColor" />
          </>
        ),
      },
      {
        label: "AIS reconciliation",
        href: "/ais",
        description:
          "Upload your Annual Information Statement and match it against your FinVigil data.",
        icon: icon(
          <>
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </>
        ),
      },
    ],
  },
  {
    label: "Analysis",
    items: [
      {
        label: "F&O P&L",
        href: "/fno",
        description: "Futures & options as business income, matched FIFO.",
        icon: icon(
          <>
            <path d="M3 3v18h18" />
            <path d="m7 14 4-4 3 3 5-6" />
          </>
        ),
      },
      {
        label: "Crypto",
        href: "/crypto",
        description: "VDA gains at 30% flat, TDS credits tracked.",
        icon: icon(
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 8.5h4a1.75 1.75 0 0 1 0 3.5h-4m0 0h4.5a1.75 1.75 0 0 1 0 3.5H9.5M11 6.5v11" />
          </>
        ),
      },
      {
        label: "Tax harvesting",
        href: "/harvesting",
        description:
          "Find losing positions to sell before March 31 and offset gains — cuts your tax bill legally.",
        icon: icon(
          <>
            <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
            <path d="M2 21c0-3 1.85-5.36 5.08-6" />
          </>
        ),
      },
    ],
  },
  {
    label: "Tools",
    items: [
      {
        label: "Replay",
        href: "/replay",
        description:
          "Rewind your portfolio to any past date and watch it evolve trade by trade.",
        icon: icon(
          <>
            <path d="M3 12a9 9 0 1 0 9-9" />
            <path d="M3 4v5h5" />
            <path d="M12 8v4l3 2" />
          </>
        ),
      },
      {
        label: "Monte Carlo",
        href: "/monte-carlo",
        description:
          "1 000-path simulation of how your portfolio might grow over time.",
        icon: icon(
          <>
            <path d="M2 20h20" />
            <path d="M5 20V9l4 4 3-8 4 6 4-8" />
          </>
        ),
      },
      {
        label: "CA export",
        href: "/export",
        description: "A capital-gains report your CA can actually use.",
        icon: icon(
          <>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <path d="M7 10l5 5 5-5" />
            <path d="M12 15V3" />
          </>
        ),
      },
      {
        label: "Journal",
        href: "/journal",
        description:
          "Voice notes on your trades — recorded, transcribed, searchable.",
        icon: icon(
          <>
            <rect x="9" y="2" width="6" height="12" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <path d="M12 19v3" />
          </>
        ),
      },
    ],
  },
  {
    label: "Account",
    items: [
      {
        label: "Brokers",
        href: "/brokers",
        description: "Connect brokers, sync trades, import tradebooks.",
        icon: icon(
          <>
            <path d="M9 17H7A5 5 0 0 1 7 7h2" />
            <path d="M15 7h2a5 5 0 1 1 0 10h-2" />
            <path d="M8 12h8" />
          </>
        ),
      },
      {
        label: "Billing",
        href: "/billing",
        description: "Manage your plan, upgrade, or cancel your subscription.",
        icon: icon(
          <>
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <path d="M2 10h20" />
          </>
        ),
      },
      {
        label: "Settings",
        href: "/settings",
        description: "Profile, theme, and preferences.",
        icon: icon(
          <>
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>
        ),
      },
    ],
  },
  {
    label: "Admin",
    items: [
      {
        label: "Dashboard",
        href: "/admin",
        description: "User counts, roles, and recent admin activity.",
        icon: icon(
          <>
            <rect x="3" y="3" width="7" height="9" rx="1" />
            <rect x="14" y="3" width="7" height="5" rx="1" />
            <rect x="14" y="12" width="7" height="9" rx="1" />
            <rect x="3" y="16" width="7" height="5" rx="1" />
          </>
        ),
      },
      {
        label: "Users",
        href: "/admin/users",
        description:
          "List users, view subscription status, toggle roles, and open a read-only support view.",
        icon: icon(
          <>
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </>
        ),
      },
      {
        label: "Feature flags",
        href: "/admin/feature-flags",
        description: "Global defaults and per-user overrides for gating features.",
        icon: icon(
          <>
            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
            <path d="M4 22v-7" />
          </>
        ),
      },
      {
        label: "ITR-3 schemas",
        href: "/admin/itr-schemas",
        description:
          "Upload each year's CBDT field-name mapping to enable ITR-3 export — no code deploy needed.",
        icon: icon(
          <>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" />
            <path d="M14 2v6h6" />
            <path d="M9 13h6M9 17h6" />
          </>
        ),
      },
    ],
  },
];

export function findNavItem(pathname: string): NavItem | undefined {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (pathname === item.href || pathname.startsWith(`${item.href}/`)) {
        return item;
      }
    }
  }
  return undefined;
}

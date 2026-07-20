"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/brand/logo";
import { NAV_GROUPS } from "@/components/shell/nav-config";
import { createClient } from "@/lib/supabase/client";

export function Sidebar({
  userEmail,
  userRole,
  onNavigate,
}: {
  userEmail: string | null;
  userRole?: string | null;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <div className="flex h-full flex-col bg-surface">
      {/* Wordmark */}
      <div className="border-b border-rule px-5 py-4">
        <Link href="/dashboard" onClick={onNavigate}>
          <Logo markSize={22} wordmarkClassName="text-xl text-ink" />
        </Link>
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
        {NAV_GROUPS.filter((g) => !g.adminOnly || userRole === "admin").map((group) => {
          const isCollapsed = collapsed[group.label] ?? false;
          return (
            <div key={group.label} className="mb-5">
              <button
                type="button"
                onClick={() =>
                  setCollapsed((c) => ({ ...c, [group.label]: !isCollapsed }))
                }
                aria-expanded={!isCollapsed}
                className="flex w-full cursor-pointer items-center justify-between px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-ink-faint hover:text-ink-muted"
              >
                {group.label}
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  className={`transition-transform ${isCollapsed ? "-rotate-90" : ""}`}
                  aria-hidden="true"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>

              {!isCollapsed && (
                <ul>
                  {group.items.map((item) => {
                    const active =
                      pathname === item.href ||
                      pathname.startsWith(`${item.href}/`);
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onNavigate}
                          aria-current={active ? "page" : undefined}
                          className={`group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors ${
                            active
                              ? "bg-brand-soft font-medium text-brand"
                              : item.soon
                                ? "text-ink-faint hover:text-ink-muted"
                                : "text-ink-muted hover:bg-bg hover:text-ink"
                          }`}
                        >
                          <span className="shrink-0">{item.icon}</span>
                          <span className="flex-1">{item.label}</span>
                          {item.soon && (
                            <span className="rounded border border-rule px-1 py-px text-[9px] uppercase tracking-wide text-ink-faint">
                              Soon
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>

      {/* User identity + logout, pinned bottom */}
      <div className="border-t border-rule px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-xs text-ink-muted" title={userEmail ?? undefined}>
              {userEmail ?? "…"}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={signingOut}
            aria-label="Log out"
            className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-bg hover:text-loss disabled:opacity-50"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="m16 17 5-5-5-5" />
              <path d="M21 12H9" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

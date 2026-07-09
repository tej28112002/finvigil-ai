"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { findNavItem } from "@/components/shell/nav-config";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

/**
 * Designed empty state for nav destinations whose pages aren't built yet
 * (BRD §7: never a blank page or dead link).
 * - Roadmap features (nav "soon" items) read as Coming soon.
 * - Stage 2B pages read as In progress.
 */
export function PagePending() {
  const pathname = usePathname();
  const item = findNavItem(pathname);

  const roadmap = item?.soon ?? false;

  return (
    <div className="flex justify-center pt-10">
      <Card className="w-full max-w-md p-8 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-md bg-brand-soft text-brand">
          {item?.icon}
        </div>
        <div className="mt-4">
          <Badge tone={roadmap ? "neutral" : "brand"}>
            {roadmap ? "Coming soon" : "In progress"}
          </Badge>
        </div>
        <h2 className="font-display mt-3 text-xl text-ink">{item?.label}</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          {item?.description}
        </p>
        <p className="mt-1 text-xs text-ink-faint">
          {roadmap
            ? "On the roadmap — it will appear here when it ships."
            : "This page is being built in the current design pass."}
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-block text-sm font-medium text-brand hover:text-brand-hover"
        >
          Back to dashboard →
        </Link>
      </Card>
    </div>
  );
}

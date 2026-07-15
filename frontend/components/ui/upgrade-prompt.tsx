import Link from "next/link";
import { Badge } from "@/components/ui/badge";

/**
 * Shown wherever a Free user hits a Pro/Premium-gated feature (a 403 from
 * the backend's check_subscription_tier()). Keep this the single place
 * that phrasing lives — every gated feature should render the same prompt,
 * not its own one-off copy.
 */
export function UpgradePrompt({ feature }: { feature: string }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-md border border-brand/30 bg-brand-soft px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-2">
        <Badge tone="brand">Pro</Badge>
        <p className="text-sm text-ink">
          Upgrade to Pro to use <span className="font-medium">{feature}</span>.
        </p>
      </div>
      <Link
        href="/billing"
        className="inline-flex h-8 shrink-0 items-center rounded-md bg-brand px-3 text-xs font-medium text-brand-fg transition-colors hover:bg-brand-hover"
      >
        Upgrade to Pro
      </Link>
    </div>
  );
}

import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { Card } from "@/components/ui/card";

/**
 * Branded 404 for any unmatched route, replacing Next's default unstyled
 * page. Links to "/" rather than a hardcoded /dashboard or /login — proxy.ts
 * already routes "/" correctly for both signed-in (→ /dashboard) and
 * signed-out (→ marketing homepage) visitors, so this doesn't need its own
 * auth check.
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6">
      <Logo markSize={24} wordmarkClassName="text-xl text-ink" className="mb-8" />
      <Card className="w-full max-w-md p-8 text-center">
        <p className="font-mono text-sm text-ink-faint">404</p>
        <h2 className="font-display mt-2 text-xl text-ink">Page not found</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          The page you&apos;re looking for doesn&apos;t exist or may have
          moved.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex h-9 items-center rounded-md bg-brand px-4 text-sm font-medium text-brand-fg hover:bg-brand-hover"
        >
          Take me home
        </Link>
      </Card>
    </div>
  );
}

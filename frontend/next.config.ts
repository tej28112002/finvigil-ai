import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next.js 15+ defaults dynamic-route client Router Cache to 0s (always
  // refetch), which is why re-visiting an already-loaded AY tab paid the
  // full server round-trip again. 30s lets a revisit within that window be
  // served instantly from the client cache instead. Mutations (Calculate,
  // Recalculate) already call router.refresh(), which explicitly bypasses
  // this cache, so they still show fresh data immediately.
  experimental: {
    staleTimes: {
      dynamic: 30,
    },
  },
  // "Rendering..." pill bottom-left is Next.js's own dev-mode activity
  // indicator — it never ships in a production build (`next build`), so it
  // was not a real production risk. Disabled here anyway for a cleaner
  // local dev screen, per request.
  devIndicators: false,
};

export default nextConfig;

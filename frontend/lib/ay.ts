/**
 * Assessment-year constants, shared by Tax/Crypto/Export/Dashboard pages.
 * Deliberately NOT in a "use client" module: Next.js treats every export of
 * a client module as a client-reference stub when imported by a Server
 * Component, even a plain string constant — importing DEFAULT_AY from
 * components/ui/ay-selector.tsx (which is "use client") into an async
 * Server Component page throws "Attempted to call DEFAULT_AY() from the
 * server" at render time. This file has no client boundary, so both
 * Server Components and Client Components can import it safely.
 */
export const DEFAULT_AY = "2026-27";
export const AY_OPTIONS = ["2026-27", "2025-26", "2024-25"];

/**
 * The REAL current assessment year, computed from today's date — mirrors
 * app.core.tax_utils.get_assessment_year() on the backend exactly (India FY
 * April–March; AY = FY end year + 1). DEFAULT_AY above is a fixed constant
 * from this project's original spec and is NOT "today" — as of when this
 * was written DEFAULT_AY/AY_OPTIONS all map to already-closed FYs. Features
 * that are inherently about "right now" (tax-loss harvesting: sell before
 * THIS year's March 31) must use this, not DEFAULT_AY, or a countdown/engine
 * built for a deadline that already passed.
 */
export function getCurrentAY(now: Date = new Date()): string {
  const fyStartYear = now.getMonth() + 1 >= 4 ? now.getFullYear() : now.getFullYear() - 1;
  const ayStartYear = fyStartYear + 1;
  const ayEndYear = ayStartYear + 1;
  return `${ayStartYear}-${String(ayEndYear).slice(2)}`;
}

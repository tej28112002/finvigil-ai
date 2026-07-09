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

import { createClient } from "@/lib/supabase/server";

// Deliberately NOT NEXT_PUBLIC_API_URL. That prefix makes Next.js inline the
// value as a literal string at BUILD TIME wherever it's referenced in
// source — including here, even though this file only ever runs
// server-side. A production incident traced to exactly this: the deployed
// build had baked in the local-dev value (127.0.0.1:8000), and there was
// no way to fix it short of a full rebuild. BACKEND_API_URL (no prefix) is
// read from real process.env at actual request time, so correcting it in
// Vercel just needs a redeploy, not a rebuild with the right value present
// at compile time. lib/api.ts (the client-side counterpart) still needs
// NEXT_PUBLIC_API_URL — the browser has no other way to learn this value.
const API_URL = process.env.BACKEND_API_URL!;

/**
 * Thrown by apiFetchServer() for any real backend failure (401/403/500/etc,
 * or a network error). Deliberately NOT thrown for 404 — see apiFetchServer.
 * Uncaught, this propagates through the page's Promise.all and is picked up
 * automatically by the nearest error.tsx boundary (Next.js App Router
 * convention) — pages don't need their own try/catch for this.
 */
export class ApiError extends Error {
  status: number;
  constructor(status: number) {
    super(`Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Reads the Supabase session from cookies once. Call this ONCE per page and
 * pass the token into every apiFetchServer() call below it — calling
 * supabase.auth.getSession() once per backend request (the old pattern)
 * measurably multiplies page load time even though the requests run in
 * Promise.all: a 3-call page paid ~6x the session-read overhead of a
 * 1-call page, not the same fixed cost, because each apiFetchServer()
 * instance re-read + re-validated the session cookie independently.
 */
export async function getServerToken(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Server-side fetch that attaches a Bearer token. Call from async Server
 * Components (no useEffect needed). Pass `token` explicitly (from a single
 * getServerToken() call at the top of the page) when making more than one
 * call per page — omit it only for single-call pages, where it falls back
 * to reading the session itself.
 *
 * Returns null ONLY for: no session, or a 404 (the resource genuinely
 * doesn't exist yet — e.g. tax not calculated for an AY — a real, expected
 * "empty" state, not a failure). Every other non-ok status (401 from a
 * stale token, 403, 500, etc.) THROWS an ApiError instead of collapsing to
 * null — previously a real backend outage was indistinguishable from "you
 * have zero holdings" because both returned null and callers rendered an
 * empty state either way. A thrown error now surfaces as a real error UI
 * via the nearest error.tsx boundary. Network failures (fetch() rejecting)
 * throw naturally and are handled the same way.
 */
export async function apiFetchServer<T>(
  path: string,
  token?: string | null
): Promise<T | null> {
  const accessToken = token === undefined ? await getServerToken() : token;
  if (!accessToken) return null;

  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new ApiError(res.status);

  return res.json() as Promise<T>;
}

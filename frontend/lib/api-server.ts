import { createClient } from "@/lib/supabase/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

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
 * Returns null on 404 or missing session so callers can render gracefully.
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

  if (!res.ok) return null;
  return res.json() as Promise<T>;
}

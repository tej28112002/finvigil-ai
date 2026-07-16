import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  // GoTrue forwards an upstream OAuth failure as an `error` query param on
  // this redirect rather than a `code` (not a guessed param name — this is
  // GoTrue's documented server-side redirect behavior). Google specifically
  // returns `error=access_denied` per RFC 6749 when the user hits "Cancel"
  // on the consent screen, and GoTrue passes that value through unchanged.
  const providerError = searchParams.get("error");
  if (providerError === "access_denied") {
    return NextResponse.redirect(`${origin}/login?error=access_denied`);
  }
  if (providerError) {
    return NextResponse.redirect(`${origin}/login?error=oauth_failed`);
  }

  if (code) {
    try {
      const supabase = await createClient();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) {
        return NextResponse.redirect(`${origin}/dashboard`);
      }
    } catch {
      // exchangeCodeForSession can throw rather than return an error object
      // (e.g. a network failure talking to Supabase) — treat that the same
      // as a returned error instead of letting it bubble into a raw 500.
    }
  }

  return NextResponse.redirect(`${origin}/login?error=oauth_failed`);
}

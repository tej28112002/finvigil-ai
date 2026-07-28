import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // getSession() reads the JWT from the cookie — no network round-trip,
  // so it adds near-zero latency per page navigation.
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const pathname = request.nextUrl.pathname;
  const isLoginRoute = pathname.startsWith("/login");
  // "/", /pricing, /about are the public marketing pages — logged-out
  // visitors must be able to reach all of them without being bounced to
  // /login. Only /login and these marketing pages are session-gated;
  // everything else (the app shell) requires a session.
  const isMarketingRoute =
    pathname === "/" || pathname === "/pricing" || pathname === "/about";
  // The OAuth provider redirects here before a session cookie exists — the
  // route handler is what creates the session (or reports the failure), so
  // it must run unauthenticated rather than get bounced to /login first.
  // /auth/confirm is the equivalent landing spot for a Supabase email
  // confirmation link, should one ever point there instead of reusing
  // /auth/callback the way the current signup flow does.
  const isAuthRoute =
    pathname.startsWith("/auth/callback") || pathname.startsWith("/auth/confirm");
  const isPublicRoute = isMarketingRoute || isLoginRoute || isAuthRoute;

  if (!session && !isPublicRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Only bounce a LOGGED-IN user off "/login" to /dashboard — they don't
  // need to log in again. The marketing homepage ("/") is never redirected
  // for anyone, logged in or not: a returning user should still be able to
  // land on it (e.g. from a bookmark or shared link) and see the "Sign in"
  // CTA, not get yanked straight into the app shell. Pricing/About are
  // likewise never gated, so a logged-in user can still view them (e.g. to
  // consider upgrading) without being forced back into the app.
  if (session && isLoginRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

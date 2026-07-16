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
  const isAuthCallbackRoute = pathname.startsWith("/auth/callback");
  const isPublicRoute = isMarketingRoute || isLoginRoute || isAuthCallbackRoute;

  if (!session && !isPublicRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Only bounce a LOGGED-IN user off "/" and "/login" to /dashboard — a
  // logged-in user should still be able to view Pricing or About (e.g.
  // to consider upgrading) without being forced back to the app shell.
  if (session && (pathname === "/" || isLoginRoute)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

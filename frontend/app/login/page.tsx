"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { FloatingCardsScene } from "@/components/brand/floating-cards-scene";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

const GOOGLE_LOGIN_ENABLED =
  process.env.NEXT_PUBLIC_GOOGLE_LOGIN_ENABLED === "true";

type Mode = "signin" | "forgot" | "forgot-sent";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageInner />
    </Suspense>
  );
}

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleNotice, setGoogleNotice] = useState(false);

  // /auth/callback redirects here with ?error=<code> when the OAuth flow
  // fails (e.g. the user cancelled on Google's consent screen). Map the
  // code to calm copy and strip it from the URL so a refresh doesn't
  // re-show a stale error.
  useEffect(() => {
    const callbackError = searchParams.get("error");
    if (callbackError === "access_denied") {
      setError("Sign-in was canceled.");
      router.replace("/login");
    } else if (callbackError) {
      setError(
        "Google sign-in failed. Please try again, or use your email and password below."
      );
      router.replace("/login");
    }
  }, [searchParams, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    router.push("/dashboard");
  }

  async function handleForgotSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(
      email,
      { redirectTo: `${window.location.origin}/login` }
    );

    setLoading(false);

    if (resetError) {
      setError(resetError.message);
      return;
    }

    setMode("forgot-sent");
  }

  function handleGoogleClick() {
    if (!GOOGLE_LOGIN_ENABLED) {
      setGoogleNotice(true);
      return;
    }
    const supabase = createClient();
    supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel — hidden on mobile, the auth card carries the page there */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-brand px-12 py-12 text-brand-fg lg:flex">
        <Logo markSize={26} wordmarkClassName="text-2xl" onBrand />

        {/* The illustrated scene — three brokers converging to one total.
            Fixed height keeps the composition legible; it sits between the
            wordmark and the headline rather than filling the whole panel. */}
        <FloatingCardsScene className="h-[280px] w-full" />

        <div className="relative max-w-md">
          <p className="font-display text-4xl leading-tight">
            All your brokers.
            <br />
            One picture.
            <br />
            <span className="italic opacity-90">Zero tax surprises.</span>
          </p>
          <div className="mt-8 flex items-start gap-3 border-t border-brand-fg/20 pt-6 text-sm">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mt-0.5 shrink-0 opacity-80"
              aria-hidden="true"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
            </svg>
            <p className="opacity-80">
              Read-only by design. FinVigil can never place a trade or move
              your money.
            </p>
          </div>
        </div>

        <p className="relative text-xs opacity-60">
          Portfolio intelligence &amp; tax clarity for Indian investors.
        </p>
      </div>

      {/* Auth card */}
      <div className="theme-transition flex flex-1 items-center justify-center bg-bg px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo markSize={22} wordmarkClassName="text-xl text-ink" />
          </div>

          {mode === "forgot-sent" ? (
            <div>
              <h1 className="font-display text-2xl text-ink">Check your email</h1>
              <p className="mt-2 text-sm text-ink-muted">
                If an account exists for <span className="text-ink">{email}</span>,
                we&apos;ve sent a link to reset your password.
              </p>
              <button
                type="button"
                onClick={() => setMode("signin")}
                className="mt-6 cursor-pointer text-sm font-medium text-brand hover:text-brand-hover"
              >
                ← Back to sign in
              </button>
            </div>
          ) : mode === "forgot" ? (
            <div>
              <h1 className="font-display text-2xl text-ink">Reset your password</h1>
              <p className="mt-2 text-sm text-ink-muted">
                Enter your email and we&apos;ll send you a reset link.
              </p>

              <form onSubmit={handleForgotSubmit} className="mt-6 space-y-4">
                <Field
                  id="forgot-email"
                  label="Email"
                  type="email"
                  value={email}
                  onChange={setEmail}
                  placeholder="you@example.com"
                />

                {error && (
                  <p className="text-sm text-loss" role="alert">
                    {error}
                  </p>
                )}

                <Button type="submit" loading={loading} className="w-full">
                  Send reset link
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError(null);
                  }}
                  className="w-full cursor-pointer text-center text-sm text-ink-muted hover:text-ink"
                >
                  ← Back to sign in
                </button>
              </form>
            </div>
          ) : (
            <div>
              <h1 className="font-display text-2xl text-ink">Log in</h1>
              <p className="mt-2 text-sm text-ink-muted">
                Welcome back to your portfolio.
              </p>

              <div className="mt-6">
                <button
                  type="button"
                  onClick={handleGoogleClick}
                  className="flex h-10 w-full cursor-pointer items-center justify-center gap-2.5 rounded-md border border-rule text-sm font-medium text-ink transition-colors hover:border-rule-strong hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-50"
                  aria-describedby={googleNotice ? "google-notice" : undefined}
                >
                  <GoogleIcon />
                  Continue with Google
                </button>
                {googleNotice && (
                  <p
                    id="google-notice"
                    role="status"
                    className="mt-2 text-xs text-ink-muted"
                  >
                    Google sign-in isn&apos;t set up yet — use email and
                    password below.
                  </p>
                )}
              </div>

              <div className="my-6 flex items-center gap-3">
                <div className="h-px flex-1 bg-rule" />
                <span className="text-xs uppercase tracking-wide text-ink-faint">
                  or
                </span>
                <div className="h-px flex-1 bg-rule" />
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <Field
                  id="email"
                  label="Email"
                  type="email"
                  value={email}
                  onChange={setEmail}
                  placeholder="you@example.com"
                />
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label htmlFor="password" className="text-sm font-medium text-ink">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setMode("forgot");
                        setError(null);
                      }}
                      className="cursor-pointer text-xs font-medium text-brand hover:text-brand-hover"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <input
                    id="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint transition-colors duration-200 focus:border-brand"
                    placeholder="••••••••"
                  />
                </div>

                {error && (
                  <p className="text-sm text-loss" role="alert">
                    {error}
                  </p>
                )}

                <Button type="submit" loading={loading} className="w-full">
                  {loading ? "Signing in…" : "Sign in"}
                </Button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        autoComplete="email"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-rule bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-faint transition-colors duration-200 focus:border-brand"
      />
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.27 14.29a7.2 7.2 0 0 1 0-4.58V6.62H1.29a12 12 0 0 0 0 10.76l3.98-3.09Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.94 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09C6.22 6.86 8.87 4.75 12 4.75Z"
      />
    </svg>
  );
}

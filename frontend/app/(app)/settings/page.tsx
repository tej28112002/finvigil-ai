"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "@/components/theme/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Card, MetricLabel } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

export default function SettingsPage() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [email, setEmail] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  const loadProfile = useCallback(async () => {
    setProfileLoading(true);
    setProfileError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setEmail(session?.user.email ?? null);
    } catch (err) {
      setProfileError(
        err instanceof Error ? err.message : "Could not load your profile"
      );
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  async function handleLogout() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card className="p-5">
        <MetricLabel>Profile</MetricLabel>
        {profileError ? (
          <div className="mt-2 flex items-center gap-3">
            <p className="text-sm text-loss" role="alert">{profileError}</p>
            <button
              type="button"
              onClick={loadProfile}
              className="cursor-pointer text-sm font-medium text-brand hover:text-brand-hover"
            >
              Try again
            </button>
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink">
            {profileLoading ? "Loading…" : (email ?? "—")}
          </p>
        )}
      </Card>

      <Card className="p-5">
        <MetricLabel>Appearance</MetricLabel>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-sm text-ink">Theme</p>
          <div className="inline-flex gap-1 rounded-md border border-rule bg-bg p-1">
            {(["light", "dark"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  if (t !== theme) toggleTheme();
                }}
                className={`cursor-pointer rounded px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                  theme === t
                    ? "bg-brand text-brand-fg"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Card>

      <Card className="p-5 opacity-60">
        <div className="flex items-center justify-between">
          <MetricLabel>Notifications</MetricLabel>
          <Badge tone="neutral">Coming soon</Badge>
        </div>
        <p className="mt-1 text-sm text-ink-muted">
          Harvest alerts, AIS mismatches, and portfolio digests.
        </p>
      </Card>

      <Card className="p-5 opacity-60">
        <div className="flex items-center justify-between">
          <MetricLabel>Shared links</MetricLabel>
          <Badge tone="neutral">Coming soon</Badge>
        </div>
        <p className="mt-1 text-sm text-ink-muted">
          Give your CA a read-only, time-limited view of your tax picture.
        </p>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <MetricLabel>Session</MetricLabel>
            <p className="mt-1 text-sm text-ink-muted">
              Sign out of FinVigil on this device.
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={signingOut}
            className="cursor-pointer rounded-md border border-rule px-3 py-1.5 text-sm font-medium text-loss transition-colors hover:bg-loss-soft disabled:opacity-50"
          >
            Log out
          </button>
        </div>
      </Card>
    </div>
  );
}

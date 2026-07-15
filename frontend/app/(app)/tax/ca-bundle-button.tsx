"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

interface ItrSchemaMapping {
  id: string;
  ay: string;
  schema_version: string;
  is_active: boolean;
  uploaded_at: string;
}

// apiFetch (lib/api.ts) always parses the response as JSON, but this
// endpoint returns a binary ZIP — so this fetches directly, mirroring
// apiFetch's auth-token attachment and error handling but returning a Blob.
async function fetchCaBundleZip(ay: string): Promise<Blob> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    window.location.href = "/login";
    throw new Error("No active session");
  }

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tax/ca-bundle`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ assessment_year: ay }),
  });

  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new Error(detail);
  }

  return res.blob();
}

export function CaBundleButton({ ay }: { ay: string }) {
  const [available, setAvailable] = useState(false);
  const [checking, setChecking] = useState(true);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setChecking(true);
    apiFetch<ItrSchemaMapping[]>("/admin/itr-schemas")
      .then((schemas) => {
        if (cancelled) return;
        setAvailable(schemas.some((s) => s.ay === ay && s.is_active));
      })
      .catch(() => {
        if (!cancelled) setAvailable(false);
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ay]);

  async function handleConfirmDownload() {
    setDownloading(true);
    setError(null);
    try {
      const blob = await fetchCaBundleZip(ay);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `finvigil_ca_bundle_${ay}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setShowDisclaimer(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed. Try again.");
    } finally {
      setDownloading(false);
    }
  }

  if (checking || !available) return null;

  return (
    <>
      <Button variant="secondary" onClick={() => setShowDisclaimer(true)}>
        Download CA Bundle (ZIP)
      </Button>

      {showDisclaimer && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ca-bundle-disclaimer-title"
        >
          <div className="w-full max-w-md rounded-md border border-rule bg-surface p-6 shadow-token-sm">
            <h2 id="ca-bundle-disclaimer-title" className="font-display text-lg text-ink">
              Before you download
            </h2>
            <p className="mt-3 text-sm text-ink-muted">
              This ZIP bundle contains your complete capital gains data for
              AY {ay}. Your CA needs this to prepare your ITR-3. It does{" "}
              <span className="font-medium text-ink">not</span> include personal
              details, salary, or TDS information.
            </p>
            {error && (
              <div className="mt-3 rounded-md border border-loss/30 bg-loss-soft px-3 py-2 text-xs text-loss">
                {error}
              </div>
            )}
            <div className="mt-5 flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowDisclaimer(false)}
                disabled={downloading}
              >
                Cancel
              </Button>
              <Button onClick={handleConfirmDownload} loading={downloading}>
                Download Bundle
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

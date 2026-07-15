"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface ItrSchemaMapping {
  id: string;
  ay: string;
  schema_version: string;
  is_active: boolean;
  uploaded_at: string;
}

export function Itr3ExportButton({ ay }: { ay: string }) {
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
      const result = await apiFetch<Record<string, unknown>>("/tax/itr3-export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assessment_year: ay }),
      });

      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `itr3_${ay}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setShowDisclaimer(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed. Try again.");
    } finally {
      setDownloading(false);
    }
  }

  if (checking || !available) return null;

  return (
    <>
      <Button variant="secondary" onClick={() => setShowDisclaimer(true)}>
        Download ITR-3 Schedule (AY {ay})
      </Button>

      {showDisclaimer && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="itr3-disclaimer-title"
        >
          <div className="w-full max-w-md rounded-md border border-rule bg-surface p-6 shadow-token-sm">
            <h2 id="itr3-disclaimer-title" className="font-display text-lg text-ink">
              Before you download
            </h2>
            <p className="mt-3 text-sm text-ink-muted">
              This file contains only your capital gains schedules (Schedule
              112A, Schedule CG, Schedule VDA). Your CA must add personal
              details, salary, house property, and TDS information before
              filing. This is <span className="font-medium text-ink">not</span> a
              complete ITR-3.
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
                I understand, download
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

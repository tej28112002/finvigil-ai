"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AYSelector } from "@/components/ui/ay-selector";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { onboarding } from "@/lib/onboarding";

export function TaxActions({ ay, equityMissing }: { ay: string; equityMissing: boolean }) {
  const router = useRouter();
  const [calculating, setCalculating] = useState(false);

  // Mark visited on client mount (localStorage — can't do this server-side).
  // A useEffect, not a render-time call: writing to localStorage during
  // render is a side effect and can double-fire under React StrictMode.
  useEffect(() => {
    onboarding.markVisitedTax();
  }, []);

  async function handleCalculate() {
    setCalculating(true);
    try {
      await apiFetch("/tax/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assessment_year: ay }),
      });
      router.refresh(); // re-renders server component with fresh equity data
    } finally {
      setCalculating(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <AYSelector value={ay} hrefFor={(next) => `/tax?ay=${next}`} />
      {equityMissing && (
        <Button onClick={handleCalculate} loading={calculating} variant="secondary">
          Calculate equity tax
        </Button>
      )}
      <Button variant="secondary" onClick={() => router.push(`/export?ay=${ay}`)}>
        Export CA report
      </Button>
    </div>
  );
}

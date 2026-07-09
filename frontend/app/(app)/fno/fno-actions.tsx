"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

export function FnoActions() {
  const router = useRouter();
  const [recalculating, setRecalculating] = useState(false);

  async function handleRecalculate() {
    setRecalculating(true);
    try {
      await apiFetch("/fno/calculate", { method: "POST" });
      router.refresh(); // re-runs the server component with fresh data
    } finally {
      setRecalculating(false);
    }
  }

  return (
    <Button onClick={handleRecalculate} loading={recalculating} variant="secondary">
      Recalculate
    </Button>
  );
}

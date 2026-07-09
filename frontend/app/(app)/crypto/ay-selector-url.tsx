"use client";

import { AYSelector } from "@/components/ui/ay-selector";

export function AYSelectorURL({ ay, basePath }: { ay: string; basePath: string }) {
  return (
    <AYSelector value={ay} hrefFor={(next) => `${basePath}?ay=${next}`} />
  );
}

"use client";

/**
 * Onboarding checklist steps 3 & 4 (BRD §8.1, Idea 10) are inherently
 * frontend/session concepts with no backend data to check against
 * ("visited /tax", "exported via this browser") — tracked as localStorage
 * flags, set the moment the real action happens. Steps 1 (broker connected)
 * and 2 (trades exist) are NOT tracked here — they're computed live from
 * real /brokers/ and /trades/ responses on every dashboard load.
 */
const KEY_VISITED_TAX = "finvigil-onboarding-visited-tax";
const KEY_EXPORTED_CA = "finvigil-onboarding-exported-ca";

function readFlag(key: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(key) === "true";
  } catch {
    return false;
  }
}

function writeFlag(key: string): void {
  try {
    window.localStorage.setItem(key, "true");
  } catch {
    // Storage unavailable (private mode etc.) — checklist step just won't persist.
  }
}

export const onboarding = {
  hasVisitedTax: () => readFlag(KEY_VISITED_TAX),
  markVisitedTax: () => writeFlag(KEY_VISITED_TAX),
  hasExportedCA: () => readFlag(KEY_EXPORTED_CA),
  markExportedCA: () => writeFlag(KEY_EXPORTED_CA),
};

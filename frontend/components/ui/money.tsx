import { formatINRParts } from "@/lib/format";

/**
 * Statement numerals — the FinVigil signature treatment for money.
 * Tabular mono digits; the ₹ symbol and paise are set lighter and smaller
 * so the rupee amount itself is the hero. Indian grouping always.
 *
 * tone: "auto" colors by sign (gain/loss/neutral); "plain" inherits.
 */
export function Money({
  value,
  size = "md",
  tone = "plain",
  signed = false,
}: {
  value: string | bigint;
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "auto" | "plain";
  signed?: boolean;
}) {
  const parts = formatINRParts(value, { signed });

  const toneClass =
    tone === "auto"
      ? parts.sign === "-"
        ? "text-loss"
        : signed && parts.sign === "+"
          ? "text-gain"
          : "text-ink"
      : "";

  const sizes = {
    sm: { main: "text-sm", side: "text-xs" },
    md: { main: "text-base", side: "text-sm" },
    lg: { main: "text-2xl", side: "text-base" },
    xl: { main: "text-4xl", side: "text-xl" },
  }[size];

  return (
    <span className={`font-mono ${toneClass}`}>
      {parts.sign && <span className={`${sizes.main} font-medium`}>{parts.sign}</span>}
      <span className={`${sizes.side} mr-0.5 opacity-60`}>{parts.symbol}</span>
      <span className={`${sizes.main} font-medium tracking-tight`}>
        {parts.integer}
      </span>
      <span className={`${sizes.side} opacity-60`}>.{parts.fraction}</span>
    </span>
  );
}

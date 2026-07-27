/**
 * FinVigil brand marks — three candidates, all pure SVG, currentColor-driven
 * so they inherit brand color and work in both themes.
 *
 * A — Vigilant Eye: an eye formed by an arc resting on a ledger rule.
 *     Vigilance over the books.
 * B — Ledger V: two staircases of ledger rows converging into one —
 *     a "V" built from the product's own structural language, and a
 *     consolidation story (many entries, one ledger) in the same shape.
 * C — Convergence: three streams (brokers) merging into a single rising
 *     line ending in one point — "All your brokers. One picture."
 *
 * The active mark is chosen in <Logo/> below; swapping is a one-line change.
 */

function VigilantEyeMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <path d="M7 31 Q24 9 41 31" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <line x1="5" y1="31" x2="43" y2="31" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="24" cy="24.5" r="5" fill="currentColor" />
    </svg>
  );
}

function LedgerVMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="currentColor" aria-hidden="true">
      <rect x="4" y="6" width="10" height="5" rx="2.5" />
      <rect x="34" y="6" width="10" height="5" rx="2.5" />
      <rect x="9" y="15" width="10" height="5" rx="2.5" />
      <rect x="29" y="15" width="10" height="5" rx="2.5" />
      <rect x="14" y="24" width="20" height="5" rx="2.5" />
      <rect x="19" y="33" width="10" height="5" rx="2.5" />
    </svg>
  );
}

export function ConvergenceMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <path d="M5 12 C16 12 19 21 25 23.2" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M5 24 L24 24" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M5 36 C16 36 19 27 25 24.8" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M25 24 C32 24 36 20 40 13.5" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="41" cy="12" r="3.25" fill="currentColor" />
    </svg>
  );
}

/**
 * Mark + wordmark lockup. Current brand mark: Convergence — strongest
 * narrative fit ("all your brokers, one picture" drawn literally as three
 * streams merging to one point). Swapping to a different candidate mark
 * is this one line.
 *
 * `onBrand`: set true when the logo sits on a --brand-colored surface (e.g.
 * the login brand panel). There, the accent must switch from --brand to
 * --brand-fg — otherwise "Vigil" and the mark render brand-on-brand and
 * vanish (the bug this prop fixes). On neutral surfaces (sidebar, auth
 * card) leave it false so "Vigil" keeps its brand-color accent.
 */
export function Logo({
  markSize = 24,
  className = "",
  wordmarkClassName = "",
  onBrand = false,
}: {
  markSize?: number;
  className?: string;
  wordmarkClassName?: string;
  onBrand?: boolean;
}) {
  const markColor = onBrand ? "text-brand-fg" : "text-brand";
  // On brand: light two-tone (Fin full, Vigil 80% — verified >4.5:1 both
  // themes). Off brand: Vigil in the brand accent color as intended.
  const accentClass = onBrand ? "text-brand-fg opacity-80" : "text-brand";

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className={markColor}>
        <ConvergenceMark size={markSize} />
      </span>
      <span className={`font-display ${wordmarkClassName}`}>
        Fin<span className={accentClass}>Vigil</span>
      </span>
    </span>
  );
}

import { Money } from "@/components/ui/money";

/**
 * Reusable illustrated composition: three broker chips visually converging
 * into one consolidated total, plus a tax-estimate badge — "all your
 * brokers, one picture, zero tax surprises" drawn as a scene rather than
 * told in a headline. CSS/SVG only, no images.
 *
 * Reused across: login brand panel (variant="login") and the marketing
 * "One Number" hero (variant="hero"). Same visual language, different scale.
 *
 * Why a variant instead of one fluid layout: the chip positions are
 * percentage-based, and percentages that read well on the ~280px login
 * panel push the chips INTO the (much larger) central card once the scene
 * is stretched to the ~460px hero panel — they collide. The hero variant
 * moves all four floating cards into the corners with real clearance around
 * a bounded central card, so nothing overlaps at any width. Both variants
 * set whitespace-nowrap on every label so a chip can never clip its own
 * text (the "Ange…" truncation bug) regardless of available width.
 *
 * Glass tint here is derived from --brand-fg (via Tailwind opacity
 * modifiers), NOT the page-level .glass utility — this composition always
 * sits on the solid --brand panel, and --brand-fg is the token already
 * verified to contrast correctly against --brand in both themes. The
 * page-level glass tokens are tuned for sitting on --bg/--surface instead
 * (used by the Header) and would look wrong here.
 *
 * Only used where visual richness is warranted (login, marketing, empty
 * states) — never on data screens.
 */
const CARD_GLASS =
  "border border-brand-fg/25 bg-brand-fg/[0.14] backdrop-blur-md";

type Variant = "login" | "hero";

// Corner-anchored positions per variant. Hero pushes further into the
// corners so the larger central card has clearance on every side.
const POSITIONS: Record<Variant, { zerodha: string; upstox: string; angelone: string; esttax: string }> = {
  login: {
    zerodha: "left-[6%] top-[14%]",
    upstox: "right-[10%] top-[8%]",
    angelone: "left-[10%] bottom-[16%]",
    esttax: "right-[8%] bottom-[8%]",
  },
  hero: {
    zerodha: "left-[4%] top-[7%]",
    upstox: "right-[5%] top-[6%]",
    angelone: "left-[5%] bottom-[9%]",
    esttax: "right-[6%] bottom-[8%]",
  },
};

export function FloatingCardsScene({
  className = "",
  variant = "login",
}: {
  className?: string;
  variant?: Variant;
}) {
  const pos = POSITIONS[variant];

  return (
    <div className={`relative ${className}`} aria-hidden="true">
      {/* Ambient glow behind the composition */}
      <div
        className="absolute left-1/2 top-1/2 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-fg opacity-[0.16] blur-3xl"
      />

      {/* Dot-grid texture */}
      <div
        className="absolute inset-0 text-brand-fg opacity-[0.14]"
        style={{
          backgroundImage: "radial-gradient(currentColor 1.2px, transparent 1.2px)",
          backgroundSize: "22px 22px",
        }}
      />

      <div className="relative flex h-full items-center justify-center [perspective:1400px]">
        {/* Broker chip stack — three sources, drifting toward one point */}
        <div
          className={`animate-float-delay absolute ${pos.zerodha} rounded-xl px-3.5 py-2.5 text-brand-fg shadow-token-lg ${CARD_GLASS}`}
          style={{ transform: "rotate(-7deg)" }}
        >
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-broker-zerodha" />
            <span className="whitespace-nowrap text-xs font-medium">Zerodha</span>
          </div>
        </div>

        <div
          className={`animate-float-slow absolute ${pos.upstox} rounded-xl px-3.5 py-2.5 text-brand-fg shadow-token-lg ${CARD_GLASS}`}
          style={{ transform: "rotate(5deg)" }}
        >
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-broker-upstox" />
            <span className="whitespace-nowrap text-xs font-medium">Upstox</span>
          </div>
        </div>

        <div
          className={`animate-float absolute ${pos.angelone} rounded-xl px-3.5 py-2.5 text-brand-fg shadow-token-lg ${CARD_GLASS}`}
          style={{ transform: "rotate(4deg)" }}
        >
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-broker-angelone" />
            <span className="whitespace-nowrap text-xs font-medium">Angel One</span>
          </div>
        </div>

        {/* Tax estimate badge — amber, honesty color, floating separately */}
        <div
          className={`animate-float absolute ${pos.esttax} rounded-xl px-3.5 py-2.5 shadow-token-lg ${CARD_GLASS}`}
          style={{ transform: "rotate(-4deg)" }}
        >
          <p className="whitespace-nowrap text-[10px] font-medium uppercase tracking-wide text-brand-fg opacity-75">
            Est. tax
          </p>
          <p className="mt-0.5 whitespace-nowrap text-sm font-semibold text-brand-fg">
            <Money value="8940.00" size="sm" />
          </p>
        </div>

        {/* The consolidated total — the convergence point, largest & centered.
            It shrinks to its own (nowrap) content, so its width is identical
            at login and hero scale. No max-w cap: the corner chips clear it
            by sitting in the top/bottom bands while the card holds the
            vertical middle — separation is by band, not by width — and a cap
            narrower than the money string would clip the total. */}
        <div
          className={`shadow-token-glow relative z-10 rounded-2xl px-7 py-5 text-brand-fg ${CARD_GLASS}`}
          style={{ transform: "rotateX(4deg) rotateY(-6deg)" }}
        >
          <p className="whitespace-nowrap text-[11px] font-medium uppercase tracking-wider opacity-75">
            Total portfolio value
          </p>
          <p className="mt-1.5 whitespace-nowrap text-3xl font-semibold tracking-tight">
            <Money value="1452300.00" size="xl" />
          </p>
          <p className="mt-1.5 whitespace-nowrap text-xs font-medium text-brand-fg">
            +₹12,480 today
          </p>
        </div>
      </div>
    </div>
  );
}

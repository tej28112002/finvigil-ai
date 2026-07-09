import Link from "next/link";
import { Button } from "@/components/ui/button";

/** Closing full-width band before the footer (BRD §6). Brand-filled, one
 * clear action. */
export function FinalCta() {
  return (
    <section className="border-t border-rule">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-24">
        <div className="relative overflow-hidden rounded-2xl bg-brand px-8 py-16 text-center text-brand-fg shadow-token-lg lg:px-16">
          {/* faint dot-grid on the brand panel */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.12]"
            style={{
              backgroundImage: "radial-gradient(currentColor 1.2px, transparent 1.2px)",
              backgroundSize: "22px 22px",
            }}
            aria-hidden="true"
          />
          <div className="relative">
            <h2 className="font-display mx-auto max-w-xl text-3xl leading-tight lg:text-4xl">
              See your one number.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-base opacity-80">
              Connect your brokers and get your complete, tax-ready portfolio
              picture — read-only, always.
            </p>
            <div className="mt-8 flex justify-center">
              <Link href="/login">
                <Button
                  variant="secondary"
                  className="h-11 border-transparent bg-brand-fg px-7 text-base text-brand hover:bg-brand-fg hover:opacity-90"
                >
                  Get started
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

import { MarketingNav } from "@/components/marketing/nav";
import { CountdownTicker } from "@/components/marketing/countdown-ticker";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { FeatureTriad } from "@/components/marketing/feature-triad";
import { ProductPeek } from "@/components/marketing/product-peek";
import { TrustSection } from "@/components/marketing/trust-section";
import { FinalCta } from "@/components/marketing/final-cta";
import { MarketingFooter } from "@/components/marketing/footer";

/**
 * Public marketing homepage (Phase 13 Stage 2C, BRD §6). Always public --
 * proxy.ts never redirects "/" regardless of session state, so a returning
 * logged-in visitor can land here too (e.g. via a bookmark or shared link)
 * rather than always being forced straight into the app shell.
 */
export default function Home() {
  return (
    <div className="theme-transition min-h-screen bg-bg">
      <MarketingNav />
      <CountdownTicker />
      <main>
        <Hero />
        <HowItWorks />
        <FeatureTriad />
        <ProductPeek />
        <TrustSection />
        <FinalCta />
      </main>
      <MarketingFooter />
    </div>
  );
}

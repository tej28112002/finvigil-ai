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
 * Public marketing homepage (Phase 13 Stage 2C, BRD §6). Logged-out
 * visitors land here; an authenticated visit to "/" is redirected to
 * /dashboard by proxy.ts before this ever renders.
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

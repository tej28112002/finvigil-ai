import { MarketingNav } from "@/components/marketing/nav";
import { MarketingFooter } from "@/components/marketing/footer";

/** Shared chrome for standalone marketing pages (Pricing, About) — same
 * nav + footer wrapper as the homepage (app/page.tsx), which composes
 * them itself since it isn't part of this route group. */
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="theme-transition min-h-screen bg-bg">
      <MarketingNav />
      <main>{children}</main>
      <MarketingFooter />
    </div>
  );
}

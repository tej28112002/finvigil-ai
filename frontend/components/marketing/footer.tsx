import { Logo } from "@/components/brand/logo";

export function MarketingFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-rule">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div>
            <Logo markSize={20} wordmarkClassName="text-base" />
            <p className="mt-3 max-w-sm text-xs text-ink-faint">
              FinVigil provides capital-gains tax estimates only — it is not
              a registered investment or tax advisor. Figures exclude cess,
              surcharge, and other income. Always confirm with your CA before
              filing.
            </p>
          </div>

          <nav className="flex gap-6 text-sm" aria-label="Footer">
            <a href="#features" className="text-ink-muted hover:text-ink">
              Features
            </a>
            <a
              href="#"
              title="Coming soon"
              aria-label="Privacy policy (coming soon)"
              className="text-ink-faint hover:text-ink-muted"
            >
              Privacy
            </a>
            <a
              href="#"
              title="Coming soon"
              aria-label="Terms of service (coming soon)"
              className="text-ink-faint hover:text-ink-muted"
            >
              Terms
            </a>
          </nav>
        </div>

        <p className="mt-8 border-t border-rule pt-6 text-xs text-ink-faint">
          © {year} FinVigil. Portfolio intelligence &amp; tax clarity for
          Indian investors.
        </p>
      </div>
    </footer>
  );
}

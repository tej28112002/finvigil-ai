"use client";

interface BrokerConnection {
  id: string;
  broker_name: string;
  status: string;
}

/**
 * Broker filter chips (BRD §8.1). Zerodha is real (from /brokers/); Angel
 * One and Upstox are decorative "not connected yet" chips — selecting them
 * is honest, not fake: there's genuinely nothing to show under them today.
 */
export function BrokerChips({
  brokers,
  selected,
  onSelect,
}: {
  brokers: BrokerConnection[];
  selected: string | null;
  onSelect: (brokerName: string | null) => void;
}) {
  const zerodha = brokers.find((b) => b.broker_name === "zerodha");

  const chip = (
    key: string | null,
    label: string,
    dotColor: string | null,
    disabled = false
  ) => {
    const active = selected === key;
    return (
      <button
        key={label}
        type="button"
        onClick={() => onSelect(key)}
        className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
          active
            ? "border-brand bg-brand-soft text-brand"
            : "border-rule text-ink-muted hover:border-rule-strong hover:text-ink"
        }`}
      >
        {dotColor && (
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: dotColor }}
            aria-hidden="true"
          />
        )}
        {label}
        {disabled && <span className="text-ink-faint">· Connect</span>}
      </button>
    );
  };

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by broker">
      {chip(null, "All brokers", null)}
      {zerodha &&
        chip(
          "zerodha",
          "Zerodha",
          zerodha.status === "active" ? "var(--gain)" : "var(--ink-faint)"
        )}
      {chip("angelone", "Angel One", "var(--ink-faint)", true)}
      {chip("upstox", "Upstox", "var(--ink-faint)", true)}
    </div>
  );
}

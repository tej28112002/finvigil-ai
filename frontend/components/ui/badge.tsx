type Tone = "estimate" | "gain" | "loss" | "neutral" | "brand";

const toneClasses: Record<Tone, string> = {
  estimate: "bg-estimate-soft text-estimate",
  gain: "bg-gain-soft text-gain",
  loss: "bg-loss-soft text-loss",
  neutral: "bg-bg text-ink-muted border border-rule",
  brand: "bg-brand-soft text-brand",
};

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium leading-4 ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}

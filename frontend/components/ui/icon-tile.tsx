const TILE_CLASSES = {
  brand: "bg-brand-soft text-brand",
  purple: "bg-accent-purple-soft text-accent-purple",
  blue: "bg-accent-blue-soft text-accent-blue",
  orange: "bg-accent-orange-soft text-accent-orange",
  neutral: "bg-bg text-ink-muted border border-rule",
} as const;

type TileColor = keyof typeof TILE_CLASSES;

/**
 * Small colored icon square for stat-card category identity (dashboard/
 * portfolio). Generalizes the bg-brand-soft/text-brand pattern already
 * used by FeatureGuideCard to the full accent palette in globals.css.
 */
export function IconTile({
  color = "neutral",
  children,
  size = 9,
}: {
  color?: TileColor;
  children: React.ReactNode;
  size?: 8 | 9 | 10;
}) {
  const sizeClass = { 8: "h-8 w-8", 9: "h-9 w-9", 10: "h-10 w-10" }[size];
  return (
    <div
      className={`flex ${sizeClass} shrink-0 items-center justify-center rounded-md ${TILE_CLASSES[color]}`}
    >
      {children}
    </div>
  );
}

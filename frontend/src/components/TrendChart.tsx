import type { SeriesPoint } from "@/lib/schemas";

export type Metric = "mood" | "sleep_hours" | "sleep_quality" | "energy" | "stress";

const WIDTH = 600;
const HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 28, left: 34 };

/**
 * A constellation of the person's own entries: one dot per day that has a value,
 * joined by a faint line. It makes no claim, and the same numbers are always
 * available as a table next to it. Color is not the only signal: position is.
 */
export function TrendChart({
  series,
  metric,
  from,
  days,
  label,
}: {
  series: readonly SeriesPoint[];
  metric: Metric;
  /** First date of the period, YYYY-MM-DD. */
  from: string;
  days: number;
  /** Full description of what the chart shows, for screen readers. */
  label: string;
}) {
  const top = metric === "sleep_hours" ? 12 : 5;
  const bottom = metric === "sleep_hours" ? 0 : 1;
  const ticks = metric === "sleep_hours" ? [0, 4, 8, 12] : [1, 2, 3, 4, 5];
  const start = Date.parse(`${from}T00:00:00Z`);
  const innerWidth = WIDTH - PAD.left - PAD.right;
  const innerHeight = HEIGHT - PAD.top - PAD.bottom;
  const x = (date: string) =>
    PAD.left +
    (Math.round((Date.parse(`${date}T00:00:00Z`) - start) / 86_400_000) / Math.max(1, days - 1)) *
      innerWidth;
  const y = (value: number) =>
    PAD.top + (1 - (Math.min(top, value) - bottom) / (top - bottom)) * innerHeight;

  const points = series
    .filter((point) => point[metric] !== null)
    .map((point) => ({ date: point.local_date, x: x(point.local_date), y: y(point[metric] as number) }));

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="h-auto w-full"
      data-chart={metric}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(tick)} y2={y(tick)} stroke="var(--line)" />
          <text
            x={PAD.left - 10}
            y={y(tick) + 4}
            textAnchor="end"
            fill="var(--moon-dim)"
            fontSize="12"
            fontFamily="var(--font-mono)"
          >
            {tick}
          </text>
        </g>
      ))}
      {points.length > 1 ? (
        <polyline
          points={points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ")}
          fill="none"
          stroke="var(--lumen)"
          strokeOpacity="0.45"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      ) : null}
      {points.map((point) => (
        <g key={point.date}>
          <circle cx={point.x} cy={point.y} r="9" fill="var(--glow)" />
          <circle cx={point.x} cy={point.y} r="4" fill="var(--lumen-hi)" />
        </g>
      ))}
    </svg>
  );
}

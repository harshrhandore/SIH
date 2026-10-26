import type { Row } from "@/lib/schemas";
import { SeriesChart } from "./series-chart";

export function PlacementChart({ rows }: { rows: Row[] }) {
  const years = new Map<string, { eligible: number; placed: number }>();
  for (const row of rows) {
    const year = String(row.year),
      current = years.get(year) || { eligible: 0, placed: 0 };
    years.set(year, {
      eligible: current.eligible + Number(row.eligible_students),
      placed: current.placed + Number(row.placed_students),
    });
  }
  return (
    <SeriesChart
      title="Placement rate by graduation year"
      maximum={100}
      suffix="%"
      caption="Distinct placed students divided by eligible students. Offers count only in the expected graduation year."
      points={[...years]
        .sort(([a], [b]) => a.localeCompare(b))
        .filter(([, row]) => row.eligible > 0)
        .map(([label, row]) => ({
          label,
          value: (100 * row.placed) / row.eligible,
        }))}
    />
  );
}

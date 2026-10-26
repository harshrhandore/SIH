import type { Row } from "@/lib/schemas";
import { SeriesChart } from "./series-chart";

export function AdmissionsChart({ rows }: { rows: Row[] }) {
  const cohorts = new Map<string, number>();
  for (const row of rows) {
    const year = String(row.year);
    cohorts.set(year, (cohorts.get(year) || 0) + Number(row.admitted));
  }
  return (
    <SeriesChart
      title="Admissions by cohort"
      caption="Students grouped by admission year, within the selected institution and program scope."
      points={[...cohorts]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([label, value]) => ({ label, value }))}
    />
  );
}

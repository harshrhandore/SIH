import type { Row } from "@/lib/schemas";
import { SeriesChart } from "./series-chart";

export function QualityChart({ rows, trend }: { rows: Row[]; trend: Row[] }) {
  return (
    <>
      <SeriesChart
        title="Record quality"
        caption="Mutually exclusive local quality statuses. Local checks do not establish official verification."
        points={
          rows.length
            ? [
                ["clean", "Clean"],
                ["flagged", "Flagged"],
                ["incomplete", "Incomplete"],
              ].map(([key, label]) => ({
                label,
                value: rows.reduce((sum, row) => sum + Number(row[key]), 0),
              }))
            : []
        }
      />
      {trend.length ? (
        <SeriesChart
          title="Clean records over time"
          mode="line"
          maximum={100}
          suffix="%"
          caption="Recorded daily quality snapshots within the current institution and state filters."
          points={trend.map((row) => ({
            label: String(row.date).slice(5),
            value: Number(row.clean_percent),
          }))}
        />
      ) : null}
    </>
  );
}

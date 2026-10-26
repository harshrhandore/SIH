import type { Row } from "@/lib/schemas";
import { SeriesChart } from "./series-chart";

export function CgpaChart({ rows }: { rows: Row[] }) {
  const buckets = [
    ["bucket_0_4", "<4"],
    ["bucket_4_6", "4–<6"],
    ["bucket_6_8", "6–<8"],
    ["bucket_8_10", "8–10"],
  ];
  return (
    <SeriesChart
      title="CGPA distribution"
      caption="Latest completed CGPA per student and academic year. A student can appear in several years; select one year for a single-year distribution."
      points={
        rows.length
          ? buckets.map(([key, label]) => ({
              label,
              value: rows.reduce((sum, row) => sum + Number(row[key]), 0),
            }))
          : []
      }
    />
  );
}

import type { Row } from "@/lib/schemas";
import { Table } from "@/components/shared/data-table";
export function MatchTable({ matches }: { matches: Row | undefined }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Field comparison</h2>
      </div>
      <Table
        rows={Object.entries(matches || {}).map(([field, score]) => ({
          field,
          score,
        }))}
        columns={[
          ["field", "Field"],
          ["score", "Similarity (0 to 1)"],
        ]}
      />
    </section>
  );
}

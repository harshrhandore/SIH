import type { Row } from "@/lib/schemas";
import { Table } from "@/components/shared/data-table";

export function FieldDiff({ versions }: { versions: Row[] }) {
  const rows = versions.flatMap((version) =>
    Object.entries((version.changed_fields || {}) as Row).map(
      ([field, value]) => {
        const change = value && typeof value === "object" ? (value as Row) : {};
        return {
          version: version.version_no,
          field,
          before: change.before ?? change.old,
          after: change.after ?? change.new,
        };
      },
    ),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Recorded field changes</h2>
      </div>
      <Table
        rows={rows}
        columns={[
          ["version", "Version"],
          ["field", "Field"],
          ["before", "Previous"],
          ["after", "Current"],
        ]}
      />
    </section>
  );
}

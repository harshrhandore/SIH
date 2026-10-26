import { Table } from "@/components/shared/data-table";
import type { Row } from "@/lib/schemas";

export function EvidenceSection({
  title,
  rows,
  columns,
  onRetry,
}: {
  title: string;
  rows: unknown;
  columns: [string, string][];
  onRetry: () => void;
}) {
  const valid =
    Array.isArray(rows) &&
    rows.every(
      (row) => row !== null && typeof row === "object" && !Array.isArray(row),
    );
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {valid ? <span className="mono">{rows.length} entries</span> : null}
      </div>
      {!valid ? (
        <div className="padded" role="alert">
          <p>
            This evidence section is unavailable. Other passport sections remain
            available.
          </p>
          <button onClick={onRetry}>Retry evidence</button>
        </div>
      ) : rows.length ? (
        <Table rows={rows as Row[]} columns={columns} />
      ) : (
        <p className="empty">No synthetic evidence supplied.</p>
      )}
    </section>
  );
}

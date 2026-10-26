"use client";
import type { Row } from "@/lib/schemas";
import { Table } from "@/components/shared/data-table";
import { number } from "@/lib/format";
export function PreviewStep({
  preview,
  batch,
  busy,
  validate,
}: {
  preview: Row[];
  batch: Row;
  busy: boolean;
  validate: () => void;
}) {
  return (
    <>
      <h2>Preview the first 20 rows</h2>
      <p className="note">
        Preview is not full-file validation. Missing identifiers remain visible
        in the source.
      </p>
      <Table
        rows={preview.map((p) => ({
          row_no: p.row_no,
          ...(p.normalized as Row),
        }))}
        columns={[
          ["row_no", "Row"],
          ["full_name", "Name"],
          ["submitted_apaar_id", "Submitted ID"],
          ["dob", "DOB"],
          ["program_code", "Program"],
        ]}
      />
      <button className="primary" disabled={busy} onClick={validate}>
        {busy
          ? "Starting validation…"
          : "Validate " + number(batch.total_rows) + " records"}
      </button>
    </>
  );
}

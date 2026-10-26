"use client";
import type { Row } from "@/lib/schemas";
const fields = [
  "submitted_apaar_id",
  "submitted_enrollment_no",
  "full_name",
  "dob",
  "parent_name",
  "program_code",
  "admission_year",
  "current_year",
  "term_no",
  "sgpa",
  "credits",
  "email",
  "gender",
];
export function MappingStep({
  batch,
  mapping,
  busy,
  setMapping,
  map,
}: {
  batch: Row;
  mapping: Record<string, string>;
  busy: boolean;
  setMapping: (value: Record<string, string>) => void;
  map: () => void;
}) {
  return (
    <>
      <h2>Map source columns</h2>
      <p className="muted">
        Mandatory fields: enrollment, name, DOB, program, admission year and
        current year. Dates use DD/MM/YYYY.
      </p>
      <div className="mapping-grid">
        {fields.map((field) => (
          <label key={field}>
            {field.replaceAll("_", " ")}
            <select
              value={mapping[field] || ""}
              onChange={(e) =>
                setMapping({ ...mapping, [field]: e.target.value })
              }
            >
              <option value="">Ignore optional column</option>
              {(batch.headers as string[]).map((h) => (
                <option key={h}>{h}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <button className="primary" disabled={busy} onClick={map}>
        {busy ? "Checking mapping…" : "Preview 20 rows"}
      </button>
    </>
  );
}

"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Upload, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { number } from "@/lib/format";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { useRequiredUser } from "@/hooks/use-current-user";

export const fields = [
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

export function ImportWizard() {
  const user = useRequiredUser();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null),
    [confirmed, setConfirmed] = useState(false),
    [batch, setBatch] = useState<Row | null>(null),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [preview, setPreview] = useState<Row[] | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function upload() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("institution_id", user.institution_id || "");
      const result = await api<Row>("/imports", { method: "POST", body: form });
      setBatch(result);
      const suggested = result.suggested_mapping as Record<
        string,
        {
          column: string;
        }
      >;
      setMapping(
        Object.fromEntries(
          Object.entries(suggested).map(([k, v]) => [k, v.column]),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function map() {
    setBusy(true);
    setError("");
    try {
      const result = await api<Row>(
        "/imports/" + batch?.batch_id + "/mapping",
        {
          method: "PUT",
          body: JSON.stringify({
            mapping: Object.fromEntries(
              Object.entries(mapping).filter(([, v]) => v),
            ),
            date_format: "DD/MM/YYYY",
          }),
        },
      );
      setPreview(result.preview as Row[]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function validate() {
    setBusy(true);
    try {
      await api("/imports/" + batch?.batch_id + "/validate", {
        method: "POST",
        body: JSON.stringify({ confirm_synthetic_data: confirmed }),
      });
      router.push("/imports/" + batch?.batch_id);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="NEW SUBMISSION"
        title="Import synthetic records"
        description="Keep the source. Check every row. Resolve discrepancies with a person."
      />
      <ol className="steps">
        {["Upload", "Map", "Preview", "Validate", "Report"].map((s, i) => (
          <li
            className={(preview ? 2 : batch ? 1 : 0) === i ? "current" : ""}
            key={s}
          >
            <span>{i + 1}</span>
            {s}
          </li>
        ))}
      </ol>
      <section className="panel padded">
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
        {!batch ? (
          <>
            <h2>Choose a source file</h2>
            <p>CSV or XLSX · up to 1,000 rows · 20 MiB maximum</p>
            <a href="/api/backend/demo/fixtures/import_csv" download>
              Download the 1,000-row synthetic fixture
            </a>
            <label className="dropzone">
              <Upload size={32} />
              <span>{file?.name || "Choose a CSV or XLSX file"}</span>
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />{" "}
              I confirm this dataset is synthetic.
            </label>
            <button
              className="primary"
              disabled={!file || !confirmed || busy}
              onClick={upload}
            >
              {busy ? "Saving source…" : "Continue to mapping"}
              <ArrowRight size={16} />
            </button>
          </>
        ) : !preview ? (
          <>
            <h2>Map source columns</h2>
            <p className="muted">
              Mandatory fields: enrollment, name, DOB, program, admission year
              and current year. Dates use DD/MM/YYYY.
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
        ) : (
          <>
            <h2>Preview the first 20 rows</h2>
            <p className="note">
              Preview is not full-file validation. Missing identifiers remain
              visible in the source.
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
        )}
      </section>
    </>
  );
}

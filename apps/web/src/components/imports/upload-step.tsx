"use client";
import { Upload, ArrowRight } from "lucide-react";
export function UploadStep({
  file,
  confirmed,
  busy,
  setFile,
  setConfirmed,
  upload,
}: {
  file: File | null;
  confirmed: boolean;
  busy: boolean;
  setFile: (file: File | null) => void;
  setConfirmed: (value: boolean) => void;
  upload: () => void;
}) {
  return (
    <>
      <h2>Choose a source file</h2>
      <p>CSV or XLSX · up to 1,000 rows · 20 MiB maximum</p>
      <details className="sample-files">
        <summary>Need a sample file?</summary>
        <a href="/api/backend/demo/fixtures/import_csv" download>
          Download 1,000 sample records (CSV)
        </a>
      </details>
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
  );
}

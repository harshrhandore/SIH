import type { Row } from "@/lib/schemas";
import { Table } from "@/components/shared/data-table";
import { text } from "@/lib/format";
export function ExtractionPanel({ d }: { d: Row }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Extracted fields</h2>
        <a
          href={"/api/backend/certificates/" + d.certificate_id + "/file"}
          download
        >
          Download source
        </a>
      </div>
      <Table
        rows={Object.entries(d.extracted as Row).map(([field, value]) => ({
          field,
          value,
        }))}
        columns={[
          ["field", "Field"],
          ["value", "Observed in document"],
        ]}
      />
      <details className="processing-details padded">
        <summary>Processing details</summary>
        <p>
          Text engine: <span>{text(d.ocr_engine)}</span>
        </p>
        <p>Extraction method: {text(d.extraction_source)}</p>
      </details>
    </section>
  );
}

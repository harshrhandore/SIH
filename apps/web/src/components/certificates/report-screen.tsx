"use client";
import Link from "next/link";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Badge } from "@/components/shared/status-badge";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function CertificateReport({ id }: { id: string }) {
  const query = useData<Row>("/certificate-verifications/" + id);
  const d = query.data,
    risk = d?.risk as Row | undefined;
  return (
    <>
      <Title
        eyebrow="SYNTHETIC · NOT OFFICIAL VERIFICATION"
        title="Local certificate consistency report"
      />
      <State {...query} retry={query.reload}>
        {d && risk ? (
          <>
            <div className="notice">
              {d.purpose === "TRIAL"
                ? "Verification trial — excluded from accepted passport and Trust Score"
                : "Passport evidence — staff acceptance is required"}
            </div>
            <div className="metrics">
              <div className="metric">
                <span>Local match confidence</span>
                <strong>
                  {Number(d.confidence).toFixed(2)}
                  <small>%</small>
                </strong>
                <Badge value={d.verdict} />
              </div>
              <div className="metric">
                <span>Heuristic risk score</span>
                <strong>
                  {text(risk.score)}
                  <small>/100</small>
                </strong>
                <Badge
                  value={
                    risk.level === "high"
                      ? "HIGH RISK — REVIEW REQUIRED"
                      : risk.level
                  }
                />
              </div>
              <div className="metric">
                <span>Text engine</span>
                <h2>{text(d.ocr_engine)}</h2>
                <p>{text(d.extraction_source)}</p>
              </div>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>Extracted fields</h2>
                <a
                  href={
                    "/api/backend/certificates/" + d.certificate_id + "/file"
                  }
                  download
                >
                  Download source
                </a>
              </div>
              <Table
                rows={Object.entries(d.extracted as Row).map(
                  ([field, value]) => ({ field, value }),
                )}
                columns={[
                  ["field", "Field"],
                  ["value", "Observed in document"],
                ]}
              />
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Heuristic risk signals</h2>
                <span>Heuristic, not validated</span>
              </div>
              <Table
                rows={risk.reasons as Row[]}
                columns={[
                  ["label", "Reason"],
                  ["weight", "Weight"],
                  ["evidence", "Measured evidence"],
                ]}
              />
              <div className="padded">
                <h3>Not assessed</h3>
                <p>{(d.not_assessed as string[]).join(" · ")}</p>
                <p>{(d.warnings as string[]).join(" ")}</p>
              </div>
            </section>
            <Link className="button" href="/certificates">
              New trial
            </Link>
          </>
        ) : null}
      </State>
    </>
  );
}

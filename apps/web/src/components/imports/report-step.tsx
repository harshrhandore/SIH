"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { number } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Badge } from "@/components/shared/status-badge";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function ImportDetail({ id }: { id: string }) {
  const query = useData<Row>("/imports/" + id, 1000);
  const d = query.data;
  const report = d?.report as Row | undefined;
  const job = d?.job as Row | undefined;
  return (
    <>
      <Title
        title={d ? text(d.filename) : "Import report"}
        description="Validation results and records that need review."
      />
      <State {...query} retry={query.reload}>
        {d && report ? (
          <>
            <section className="panel padded">
              <Badge value={d.status} />
              <div className="spread">
                <h2>
                  {number(report.processed_rows)} / {number(report.total_rows)}{" "}
                  records processed
                </h2>
                <span className="mono">{text(job?.progress || 0)}%</span>
              </div>
              <div className="progress">
                <div style={{ width: text(job?.progress || 0) + "%" }} />
              </div>
              {d.status === "FAILED" ? (
                <div className="error">
                  {text(job?.error_message)}
                  <button
                    onClick={async () => {
                      await api("/import-jobs/" + job?.id + "/retry", {
                        method: "POST",
                        body: JSON.stringify({
                          reason:
                            "Retry the interrupted synthetic import from its checkpoint.",
                        }),
                      });
                      query.reload();
                    }}
                  >
                    Retry saved checkpoint
                  </button>
                </div>
              ) : null}
            </section>
            <div className="metrics">
              {[
                ["clean", "Passed local checks"],
                ["flagged", "Flagged for review"],
                ["incomplete", "Incomplete"],
                ["affected_rows", "Need attention"],
              ].map(([key, label]) => (
                <div className="metric" key={key}>
                  <span>{label}</span>
                  <strong>{number(report[key])}</strong>
                </div>
              ))}
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>Primary findings</h2>
                <a href={"/api/backend/imports/" + id + "/errors.csv"} download>
                  Download error CSV
                </a>
              </div>
              <Table
                rows={report.primary_findings as Row[]}
                columns={[
                  ["code", "Rule"],
                  ["count", "Affected rows"],
                ]}
              />
              <div className="padded">
                <p>
                  {number(report.secondary_findings)} secondary findings ·{" "}
                  {number(report.all_findings)} findings in total
                </p>
                <Link className="primary" href="/cases">
                  Open cases <ArrowRight size={16} />
                </Link>{" "}
                <Link className="button" href="/dashboard">
                  View institution ledger
                </Link>
              </div>
            </section>
          </>
        ) : null}
      </State>
    </>
  );
}

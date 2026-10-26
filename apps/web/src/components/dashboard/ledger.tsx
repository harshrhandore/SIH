"use client";
import Link from "next/link";
import { Upload, ArrowUpRight, ArrowRight } from "lucide-react";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { number } from "@/lib/format";
import { useLiveDashboard } from "@/hooks/use-live-dashboard";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function Dashboard() {
  const query = useLiveDashboard();
  const d = query.data;
  return (
    <>
      <Title
        title="Institution ledger"
        description={
          d
            ? text(d.institution_name)
            : "Your institution’s live record quality and review activity."
        }
      >
        <Link className="primary" href="/imports/new">
          <Upload size={17} /> Import records
        </Link>
      </Title>
      <State {...query} retry={query.reload}>
        {d ? (
          <>
            <div className="metrics">
              {[
                ["total", "Total records"],
                ["clean", "Passed local checks"],
                ["flagged", "Flagged for review"],
                ["incomplete", "Incomplete"],
              ].map(([key, label], i) => (
                <Link
                  href={"/students?quality=" + key}
                  className={"metric metric-" + i}
                  key={key}
                >
                  <div className="metric-label">
                    {label}
                    <ArrowUpRight size={16} />
                  </div>
                  <strong>{number(d[key])}</strong>
                </Link>
              ))}
            </div>
            <div className="two-columns">
              <section className="panel submission">
                <div className="panel-heading">
                  <h2>Submission coverage</h2>
                  <span className="mono">{text(d.submission_percent)}%</span>
                </div>
                <div className="progress">
                  <div style={{ width: text(d.submission_percent) + "%" }} />
                </div>
                <div className="spread">
                  <p>
                    <b>{number(d.total)}</b> submitted
                  </p>
                  <p>
                    <b>{number(d.missing_records)}</b> missing records
                  </p>
                </div>
                <p className="note">
                  Measured against this institution’s expected record count.
                </p>
              </section>
              <section className="panel review-card">
                <h2>{number(d.pending_reviews)} records need attention</h2>
                <p className="muted">
                  {number(d.pending_corrections)} pending operator corrections.
                </p>
                <Link href="/cases">
                  Open review queue <ArrowRight size={16} />
                </Link>
              </section>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Recent submissions</h2>
                </div>
                <Link href="/imports">
                  View all <ArrowRight size={15} />
                </Link>
              </div>
              <Table
                rows={d.recent_imports as Row[]}
                columns={[
                  ["filename", "Source file"],
                  ["total_rows", "Records"],
                  ["clean_rows", "Passed"],
                  ["flagged_rows", "Flagged"],
                  ["status", "Status"],
                ]}
                href={(r) => "/imports/" + r.id}
              />
            </section>
          </>
        ) : null}
      </State>
    </>
  );
}

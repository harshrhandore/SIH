"use client";
import { api } from "@/lib/api";
import type { Row } from "@/lib/schemas";
import { text, number } from "@/lib/format";
import { Badge } from "@/components/shared/status-badge";
export function ProgressStep({
  d,
  report,
  job,
  onRetry,
}: {
  d: Row;
  report: Row;
  job: Row | undefined;
  onRetry: () => void;
}) {
  return (
    <section className="panel padded">
      <Badge value={d.status} />
      <div className="spread">
        <h2>
          {number(report.processed_rows)} / {number(report.total_rows)} records
          processed
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
              onRetry();
            }}
          >
            Retry saved checkpoint
          </button>
        </div>
      ) : null}
    </section>
  );
}

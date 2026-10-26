"use client";
import { CheckCircle2, Clock3, RefreshCw } from "lucide-react";
import { Row } from "@/lib/schemas";
import { Envelope } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";

export function Timeline({ id }: { id: string }) {
  const query = useData<Envelope>("/students/" + id + "/timeline");
  return (
    <>
      <Title
        eyebrow="ACCOUNTABLE HISTORY"
        title="Audit timeline"
        description="Ticks require verification of the full institution chain containing each event."
      >
        <button onClick={query.reload}>
          <RefreshCw size={16} /> Verify chain
        </button>
      </Title>
      <State {...query} retry={query.reload}>
        {query.data ? (
          <section className="panel padded">
            <p className="notice">
              {query.data.verified
                ? "Full chain verified"
                : "Chain verification failed or unavailable"}{" "}
              · checked head {text(query.data.checked_head_seq)}
            </p>
            <div className="timeline">
              {query.data.items.map((row) => (
                <article key={text(row.event_id)}>
                  <div className="timeline-dot">
                    {row.hash_verified ? (
                      <CheckCircle2 size={17} />
                    ) : (
                      <Clock3 size={17} />
                    )}
                  </div>
                  <div className="eyebrow">
                    {text(row.occurred_at)} · #{text(row.sequence_no)}
                  </div>
                  <h3>{text(row.action).replaceAll("_", " ")}</h3>
                  <p>{text(row.reason)}</p>
                  <p className="muted">{text(row.actor_name)}</p>
                  {Object.keys((row.changes as Row) || {}).length ? (
                    <pre>{JSON.stringify(row.changes, null, 2)}</pre>
                  ) : null}
                  <details>
                    <summary>Stored row hash</summary>
                    <code>{text(row.row_hash)}</code>
                  </details>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </State>
    </>
  );
}

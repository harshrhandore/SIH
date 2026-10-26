"use client";
import { CheckCircle2, Clock3, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Row } from "@/lib/schemas";
import { Envelope } from "@/lib/schemas";
import { text, kolkataDateTime } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";

export function Timeline({ id }: { id: string }) {
  const [page, setPage] = useState(1);
  const size = 25;
  const query = useData<Envelope>(
    "/students/" + id + "/timeline?page=" + page + "&page_size=" + size,
  );
  return (
    <>
      <Title
        title="Audit timeline"
        description="Changes to this record, who made them and why."
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
                : "Chain verification failed or unavailable"}
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
                    {kolkataDateTime(text(row.occurred_at))} · #
                    {text(row.sequence_no)}
                  </div>
                  <h3>{text(row.action).replaceAll("_", " ")}</h3>
                  <p>{text(row.reason)}</p>
                  <p className="muted">{text(row.actor_name)}</p>
                  {Object.keys((row.changes as Row) || {}).length ? (
                    <details>
                      <summary>View changes</summary>
                      <pre>{JSON.stringify(row.changes, null, 2)}</pre>
                    </details>
                  ) : null}
                  <details>
                    <summary>Stored row hash</summary>
                    <code>{text(row.row_hash)}</code>
                  </details>
                </article>
              ))}
            </div>
            {!query.data.items.length ? (
              <div className="empty">
                <p>No events recorded yet.</p>
                <Link href={"/students/" + id}>Return to passport</Link>
              </div>
            ) : null}
            {query.data.total > size ? (
              <div className="pagination">
                <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                  Previous events
                </button>
                <span>
                  Page {page} · {query.data.total} events
                </span>
                <button
                  disabled={page * size >= query.data.total}
                  onClick={() => setPage(page + 1)}
                >
                  Next events
                </button>
              </div>
            ) : null}
          </section>
        ) : null}
      </State>
    </>
  );
}

"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { Envelope, Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { useRequiredUser } from "@/hooks/use-current-user";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { SeriesChart } from "@/components/charts/series-chart";

export function Oversight() {
  const user = useRequiredUser();
  const router = useRouter();
  const params = useSearchParams();
  const state = params.get("state") || "",
    inst = params.get("institution_id") || "",
    program = params.get("program_id") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const size = 25;
  const filters = new URLSearchParams({
    ...(state ? { state } : {}),
    ...(inst ? { institution_id: inst } : {}),
    ...(program ? { program_id: program } : {}),
    page: String(page),
    page_size: String(size),
  });
  const query = useData<Envelope>(
    user.role === "ADMIN" ? "/oversight?" + filters.toString() : null,
  );
  const institutions = useData<Envelope>(
    user.role === "ADMIN" ? "/institutions" : null,
  );
  const programs = useData<Envelope>(
    user.role === "ADMIN" && inst
      ? "/institutions/" + encodeURIComponent(inst) + "/programs"
      : null,
  );
  function change(key: string, value: string) {
    const next = new URLSearchParams(filters);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    if (key === "state") {
      next.delete("institution_id");
      next.delete("program_id");
    }
    if (key === "institution_id") next.delete("program_id");
    router.replace("/oversight?" + next.toString());
  }
  if (user.role !== "ADMIN")
    return (
      <div className="empty">
        <h1>Aggregate oversight</h1>
        <p>This view is available to administrator accounts.</p>
      </div>
    );
  const trend = (query.data?.trend as Row[] | undefined) || [];
  return (
    <>
      <Title
        title="Institution oversight"
        description="Submission coverage and discrepancies. No raw student records in this view."
      />
      <section className="panel">
        <div className="filters">
          <label>
            State
            <select
              value={state}
              onChange={(event) => change("state", event.target.value)}
            >
              <option value="">All states</option>
              {[
                ...new Set(
                  institutions.data?.items.map((row) => String(row.state)) ||
                    [],
                ),
              ]
                .sort()
                .map((value) => (
                  <option key={value}>{value}</option>
                ))}
            </select>
          </label>
          <label>
            Institution
            <select
              value={inst}
              onChange={(event) => change("institution_id", event.target.value)}
            >
              <option value="">All institutions</option>
              {institutions.data?.items
                .filter((row) => !state || row.state === state)
                .map((row) => (
                  <option key={text(row.id)} value={text(row.id)}>
                    {text(row.name)}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Program
            <select
              value={program}
              disabled={!inst || programs.loading}
              onChange={(event) => change("program_id", event.target.value)}
            >
              <option value="">All programs</option>
              {programs.data?.items.map((row) => (
                <option key={text(row.id)} value={text(row.id)}>
                  {text(row.name)}
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => router.replace("/oversight")}>
            Clear filters
          </button>
        </div>
        {institutions.error || programs.error ? (
          <p className="error" role="alert">
            {(institutions.error || programs.error)?.message}
            <button
              onClick={() => {
                institutions.reload();
                programs.reload();
              }}
            >
              Retry filters
            </button>
          </p>
        ) : null}
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["institution_name", "Institution"],
              ["state", "State"],
              ["total", "Records"],
              ["submission_percent", "Submitted %"],
              ["missing_records", "Missing"],
              ["unresolved_discrepancies", "Discrepancies"],
              ["pending_reviews", "Pending review"],
            ]}
          />
          {query.data && query.data.total > size ? (
            <div className="pagination">
              <button
                disabled={page === 1}
                onClick={() => change("page", String(page - 1))}
              >
                Previous institutions
              </button>
              <span>
                Page {page} &middot; {query.data.total} institutions
              </span>
              <button
                disabled={page * size >= query.data.total}
                onClick={() => change("page", String(page + 1))}
              >
                Next institutions
              </button>
            </div>
          ) : null}
          {trend.length && !program ? (
            <SeriesChart
              title="Clean records over time"
              maximum={100}
              suffix="%"
              mode="line"
              caption="Daily aggregate snapshots within the selected institution and state scope."
              points={trend.map((row) => ({
                label: String(row.date).slice(5),
                value: Number(row.clean_percent),
              }))}
            />
          ) : program ? (
            <p className="note padded">
              Historical quality snapshots are not recorded separately by
              program.
            </p>
          ) : null}
        </State>
      </section>
      <Link className="button" href="/cases">
        Open masked case queue
      </Link>
    </>
  );
}

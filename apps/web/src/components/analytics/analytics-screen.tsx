"use client";
import { useState, useRef, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Envelope, Row } from "@/lib/schemas";
import { text, kolkataDateTime } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { useRequiredUser } from "@/hooks/use-current-user";
import { AdmissionsChart } from "@/components/charts/admissions-chart";
import { PlacementChart } from "@/components/charts/placement-chart";
import { CgpaChart } from "@/components/charts/cgpa-chart";
import { QualityChart } from "@/components/charts/quality-chart";

export function Analytics() {
  const user = useRequiredUser();
  const [kind, setKind] = useState("admissions");
  const [inst, setInst] = useState(
    user.institution_id || user.assigned_institutions[0] || "",
  );
  const institutions = useData<Envelope>("/institutions");
  const [program, setProgram] = useState("");
  const [year, setYear] = useState("");
  const [state, setState] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<ApiError | null>(null);
  const [refreshMessage, setRefreshMessage] = useState("");
  const refreshControl = useRef<AbortController | null>(null);
  useEffect(() => () => refreshControl.current?.abort(), []);
  const programs = useData<Envelope>(
    inst ? "/institutions/" + inst + "/programs" : null,
  );
  const filters = new URLSearchParams({
    ...(inst ? { institution_id: inst } : {}),
    ...(program ? { program_id: program } : {}),
    ...(year && kind !== "data-quality" ? { year } : {}),
    ...(state ? { state } : {}),
  });
  const query = useData<Envelope>(
    "/analytics/" + kind + "?" + filters.toString(),
    5000,
  );
  async function refreshAnalytics() {
    type RefreshStatus = {
      status: string;
      stale: boolean;
      views: { name: string; refreshed_at: string | null }[];
    };
    const controller = new AbortController();
    refreshControl.current?.abort();
    refreshControl.current = controller;
    const signal = controller.signal;
    setRefreshing(true);
    setRefreshError(null);
    setRefreshMessage("");
    try {
      const before = await api<RefreshStatus>("/analytics/refresh-status", {
        signal,
      });
      const timestamps = new Map(
        before.views.map((view) => [
          view.name,
          new Date(view.refreshed_at || 0).getTime(),
        ]),
      );
      await api("/analytics/refresh", { method: "POST", body: "{}", signal });
      setRefreshMessage("Refreshing analytics. Waiting for updated data…");
      for (let attempt = 0; attempt < 30; attempt++) {
        if (signal.aborted) return;
        const status = await api<RefreshStatus>("/analytics/refresh-status", {
          signal,
        });
        if (
          status.status === "READY" &&
          !status.stale &&
          status.views.length &&
          status.views.every(
            (view) =>
              new Date(view.refreshed_at || 0).getTime() >
              (timestamps.get(view.name) || 0),
          )
        ) {
          await query.reload();
          setRefreshMessage(
            "Analytics refreshed at " +
              kolkataDateTime(status.views[0].refreshed_at!),
          );
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      throw new ApiError(
        "REFRESH_PENDING",
        "Refresh has not completed yet. Retry or inspect the current view timestamp.",
      );
    } catch (error) {
      if (!signal.aborted) {
        setRefreshError(error as ApiError);
        setRefreshMessage("");
      }
    } finally {
      if (!signal.aborted) setRefreshing(false);
    }
  }
  const columns: Record<string, [string, string][]> = {
    admissions: [
      ["year", "Cohort"],
      ...(inst ? [["program_name", "Program"] as [string, string]] : []),
      ["admitted", "Admitted"],
    ],
    placements: [
      ["year", "Graduation year"],
      ["eligible_students", "Eligible students"],
      ["placed_students", "Placed students"],
      ["placement_rate", "Rate %"],
      ["median_package_lpa", "Median LPA"],
      ["max_package_lpa", "Maximum LPA"],
    ],
    performance: [
      ["year", "Year"],
      ["branch", "Branch"],
      ["assessed_students", "Assessed"],
      ["avg_cgpa", "Average CGPA"],
      ["pass_percent", "Pass %"],
    ],
    "data-quality": [
      ["total", "Total"],
      ["clean", "Clean"],
      ["flagged", "Flagged"],
      ["incomplete", "Incomplete"],
      ["submission_percent", "Submission %"],
    ],
  };
  const tableRows =
    kind === "admissions"
      ? inst
        ? (query.data?.items || []).map((row) => ({
            ...row,
            program_name:
              programs.data?.items.find(
                (program) => program.id === row.program_id,
              )?.name || "Program name unavailable",
          }))
        : Array.from(
            (query.data?.items || []).reduce((years, row) => {
              const year = String(row.year);
              years.set(year, (years.get(year) || 0) + Number(row.admitted));
              return years;
            }, new Map<string, number>()),
            ([year, admitted]) => ({ year, admitted }),
          ).sort((a, b) => a.year.localeCompare(b.year))
      : query.data?.items || [];
  return (
    <>
      <Title
        title="Analytics"
        description="Admissions, academic performance and record quality across your institutions."
      >
        <button
          disabled={refreshing || Boolean(query.data?.refreshing)}
          onClick={refreshAnalytics}
        >
          <RefreshCw size={16} />{" "}
          {refreshing || query.data?.refreshing ? "Refreshing…" : "Refresh now"}
        </button>
      </Title>
      {refreshError ? (
        <p className="error" role="alert">
          {refreshError.message} <small>{refreshError.requestId}</small>
        </p>
      ) : null}
      <p className="note" role="status">
        {refreshMessage}
      </p>
      <section className="panel">
        <div className="filters">
          <label>
            Institution
            <select
              value={inst}
              onChange={(e) => {
                setInst(e.target.value);
                setProgram("");
              }}
            >
              <option value="">All authorized institutions</option>
              {institutions.data?.items
                .filter((r) => !state || r.state === state)
                .map((r) => (
                  <option key={text(r.id)} value={text(r.id)}>
                    {text(r.name)}
                  </option>
                ))}
            </select>
          </label>
          {user.role === "ADMIN" ? (
            <label>
              State
              <select
                value={state}
                onChange={(event) => {
                  setState(event.target.value);
                  setInst("");
                  setProgram("");
                }}
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
          ) : null}
          <label>
            Program
            <select
              value={program}
              disabled={!inst || programs.loading}
              onChange={(event) => setProgram(event.target.value)}
            >
              <option value="">All programs</option>
              {programs.data?.items.map((row) => (
                <option key={text(row.id)} value={text(row.id)}>
                  {text(row.name)}
                </option>
              ))}
            </select>
          </label>
          {kind !== "data-quality" ? (
            <label>
              Year
              <select
                value={year}
                onChange={(event) => setYear(event.target.value)}
              >
                <option value="">All years</option>
                {Array.from({ length: 9 }, (_, index) => 2022 + index).map(
                  (value) => (
                    <option key={value}>{value}</option>
                  ),
                )}
              </select>
            </label>
          ) : null}
          <label>
            View
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {["admissions", "placements", "performance", "data-quality"].map(
                (k) => (
                  <option key={k} value={k}>
                    {
                      {
                        admissions: "Admissions",
                        placements: "Placements",
                        performance: "Academic performance",
                        "data-quality": "Record quality",
                      }[k]
                    }
                  </option>
                ),
              )}
            </select>
          </label>
          <button
            type="button"
            onClick={() => {
              setInst(
                user.institution_id || user.assigned_institutions[0] || "",
              );
              setProgram("");
              setState("");
              setYear("");
            }}
          >
            Clear filters
          </button>
        </div>
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <p className="note padded">
                Updated {kolkataDateTime(text(query.data.data_as_of))}
                {query.data.stale ? " · An update is pending" : ""}
              </p>
              {kind === "admissions" ? (
                <AdmissionsChart rows={query.data.items} />
              ) : kind === "placements" ? (
                <PlacementChart rows={query.data.items} />
              ) : kind === "performance" ? (
                <CgpaChart rows={query.data.items} />
              ) : (
                <QualityChart
                  rows={query.data.items}
                  trend={(query.data.trend as Row[] | undefined) || []}
                />
              )}
              <Table rows={tableRows} columns={columns[kind]} />
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}

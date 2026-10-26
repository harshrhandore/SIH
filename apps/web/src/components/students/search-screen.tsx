"use client";
import { LatencyChip } from "@/components/shared/latency-chip";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { Search } from "lucide-react";
import { Envelope } from "@/lib/schemas";
import { number } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function SearchScreen() {
  const statusFilter = useSearchParams().get("quality");
  const [input, setInput] = useState(""),
    [q, setQ] = useState(""),
    [branch, setBranch] = useState(""),
    [year, setYear] = useState(""),
    [page, setPage] = useState(1);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(input);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [input]);
  const query = useData<Envelope>(
    "/students/search?" +
      new URLSearchParams({
        q,
        branch,
        ...(year ? { current_year: year } : {}),
        ...(statusFilter ? { quality: statusFilter } : {}),
        page: String(page),
      }).toString(),
  );
  return (
    <>
      <Title
        title="Student search"
        description="Find students by name, enrollment number or synthetic identifier."
      />
      <section className="panel">
        <div className="filters">
          {statusFilter ? (
            <span className="notice">
              Status: {statusFilter}{" "}
              <Link href="/students">Clear status filter</Link>
            </span>
          ) : null}
          <label className="search-field">
            <Search size={18} />
            <input
              name="student-search"
              autoComplete="off"
              aria-label="Search student records"
              placeholder="Name, synthetic ID or enrollment number"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          <label>
            Branch
            <select
              value={branch}
              onChange={(e) => {
                setBranch(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All branches</option>
              {["CSE", "ECE", "ME", "IT", "AI&DS", "GENERAL"].map((b) => (
                <option key={b}>{b}</option>
              ))}
            </select>
          </label>
          <label>
            Year
            <select
              value={year}
              onChange={(e) => {
                setYear(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All years</option>
              {[1, 2, 3, 4].map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </label>
          <button
            onClick={() => {
              setInput("");
              setBranch("");
              setYear("");
              setPage(1);
            }}
          >
            Clear
          </button>
        </div>
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <details className="padded">
                <summary>Search timing</summary>
                <LatencyChip
                  cache={query.data.cache}
                  tookMs={query.data.took_ms}
                />
              </details>
              <div className="search-summary" role="status">
                Found <b>{number(query.data.total)}</b>{" "}
                {query.data.total === 1 ? "record" : "records"}
              </div>
              <Table
                rows={query.data.items}
                columns={[
                  ["full_name", "Student name"],
                  ["apaar_id", "Synthetic identifier"],
                  ["program", "Program"],
                  ["current_year", "Year"],
                  ["data_quality_status", "Local status"],
                ]}
                href={(r) => "/students/" + r.id}
              />
              {query.data.total > 25 ? (
                <div className="pagination">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  <span>
                    Page {page} · {number(query.data.total)} records
                  </span>
                  <button
                    disabled={page * 25 >= query.data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              ) : null}
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}

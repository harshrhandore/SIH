"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, FileText } from "lucide-react";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { Badge } from "@/components/shared/status-badge";

export function Table({
  rows,
  columns,
  href,
}: {
  rows: Row[];
  columns: [string, string][];
  href?: (row: Row) => string;
}) {
  const [compact, setCompact] = useState(false);
  if (!rows.length)
    return (
      <div className="empty">
        <FileText />
        <h3>No records to display</h3>
        <p>Try clearing your filters or complete a synthetic import.</p>
      </div>
    );
  return (
    <>
      <div className="table-tools" role="group" aria-label="Table row density">
        <span>Row density</span>
        <button
          type="button"
          className="secondary"
          aria-pressed={compact}
          onClick={() => setCompact(!compact)}
        >
          {compact ? "Compact · 32 px" : "Comfortable · 44 px"}
        </button>
      </div>
      <div
        className="table-scroll"
        data-density={compact ? "compact" : "comfortable"}
        tabIndex={0}
        role="region"
        aria-label="Scrollable record table"
      >
        <table>
          <thead>
            <tr>
              {columns.map(([key, label]) => (
                <th key={key}>{label}</th>
              ))}
              {href ? (
                <th>
                  <span className="sr-only">Open record</span>
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={text(r.id || r.case_id || i)}>
                {columns.map(([key]) => (
                  <td key={key}>
                    {key.includes("status") ? (
                      <Badge value={r[key]} />
                    ) : key === "full_name" && href ? (
                      <Link className="record-link" href={href(r)}>
                        {text(r[key])}
                      </Link>
                    ) : (
                      text(r[key])
                    )}
                  </td>
                ))}
                {href ? (
                  <td>
                    <Link
                      aria-label={
                        "Open " +
                        text(r.full_name || r.filename || r.id || r.case_id)
                      }
                      href={href(r)}
                    >
                      <ArrowUpRight size={17} />
                    </Link>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

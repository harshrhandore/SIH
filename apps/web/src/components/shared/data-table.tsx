"use client";
import Link from "next/link";
import { useId } from "react";
import { ArrowUpRight } from "lucide-react";
import { Row } from "@/lib/schemas";
import { text, kolkataDateTime } from "@/lib/format";
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
  const tableId = useId();
  const linkedColumn = href
    ? columns.find(([key]) =>
        ["full_name", "masked_name", "filename"].includes(key),
      )?.[0]
    : undefined;
  if (!rows.length) return <p className="table-empty">No records to display</p>;
  return (
    <div className="record-table">
      <table role="table">
        <thead role="rowgroup">
          <tr role="row">
            {columns.map(([key, label]) => (
              <th
                key={key}
                id={`${tableId}-${key}`}
                scope="col"
                role="columnheader"
              >
                {label}
              </th>
            ))}
            {href && !linkedColumn ? (
              <th id={`${tableId}-open`} scope="col" role="columnheader">
                <span className="sr-only">Open record</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody role="rowgroup">
          {rows.map((r, i) => (
            <tr key={text(r.id || r.case_id || i)} role="row">
              {columns.map(([key, label]) => (
                <td key={key} headers={`${tableId}-${key}`} role="cell">
                  <span className="cell-label" aria-hidden="true">
                    {label}
                  </span>
                  <span className="cell-value">
                    {key.includes("status") ? (
                      <Badge value={r[key]} />
                    ) : key === linkedColumn && href ? (
                      <Link className="record-link" href={href(r)}>
                        {text(
                          r[key] ||
                            (key === "filename"
                              ? "Unnamed file"
                              : "Name not provided"),
                        )}
                      </Link>
                    ) : key.endsWith("_at") && typeof r[key] === "string" ? (
                      kolkataDateTime(String(r[key]))
                    ) : (
                      text(r[key])
                    )}
                  </span>
                </td>
              ))}
              {href && !linkedColumn ? (
                <td headers={`${tableId}-open`} role="cell">
                  <span className="cell-label" aria-hidden="true">
                    Record
                  </span>
                  <Link
                    aria-label={
                      "Open " +
                      text(r.full_name || r.filename || r.id || r.case_id)
                    }
                    href={href(r)}
                  >
                    Open record <ArrowUpRight size={15} aria-hidden="true" />
                  </Link>
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

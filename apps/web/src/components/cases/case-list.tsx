"use client";
import { useState } from "react";
import { Envelope } from "@/lib/schemas";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function Cases() {
  const [status, setStatus] = useState("OPEN"),
    [q, setQ] = useState("");
  const query = useData<Envelope>(
    "/cases?" + new URLSearchParams({ status, q }).toString(),
  );
  return (
    <>
      <Title
        eyebrow="HUMAN REVIEW"
        title="Verification cases"
        description="Inspect the evidence. Record the reason. Keep every decision traceable."
      />
      <section className="panel">
        <div className="filters">
          <label>
            Case status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {[
                "OPEN",
                "CORRECTION_REQUESTED",
                "ESCALATED",
                "APPROVED",
                "",
              ].map((v) => (
                <option key={v} value={v}>
                  {v || "All statuses"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Enrollment or name
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="DEMO-A-0032"
            />
          </label>
        </div>
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["full_name", "Student"],
              ["masked_name", "Masked name"],
              ["submitted_enrollment_no", "Enrollment"],
              ["opened_reason", "Primary rule"],
              ["status", "Status"],
            ]}
            href={(r) => "/cases/" + (r.id || r.case_id)}
          />
        </State>
      </section>
    </>
  );
}

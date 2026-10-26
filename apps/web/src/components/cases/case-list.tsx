"use client";
import { CaseFilters } from "./case-filters";
import { useState } from "react";
import { Envelope } from "@/lib/schemas";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { useRequiredUser } from "@/hooks/use-current-user";

export function Cases() {
  const user = useRequiredUser();
  const [status, setStatus] = useState("OPEN"),
    [q, setQ] = useState("");
  const query = useData<Envelope>(
    "/cases?" + new URLSearchParams({ status, q }).toString(),
  );
  return (
    <>
      <Title
        title="Verification cases"
        description="Review flagged records and record your decision."
      />
      <section className="panel">
        <CaseFilters status={status} q={q} setStatus={setStatus} setQ={setQ} />
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              [user.role === "ADMIN" ? "masked_name" : "full_name", "Student"],
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

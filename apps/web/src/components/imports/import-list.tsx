"use client";
import Link from "next/link";
import { Upload } from "lucide-react";
import { Envelope } from "@/lib/schemas";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";

export function ImportList() {
  const query = useData<Envelope>("/imports");
  return (
    <>
      <Title
        title="Imports"
        description="Uploaded files and their validation results."
      >
        <Link className="primary" href="/imports/new">
          <Upload size={17} /> Import records
        </Link>
      </Title>
      <section className="panel">
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["filename", "Source file"],
              ["total_rows", "Records"],
              ["clean_rows", "Passed"],
              ["flagged_rows", "Flagged"],
              ["status", "Status"],
            ]}
            href={(r) => "/imports/" + r.id}
          />
        </State>
      </section>
    </>
  );
}

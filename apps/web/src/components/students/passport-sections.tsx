"use client";
import Link from "next/link";
import { ProfileHeader } from "./profile-header";
import { TermMatrix } from "./term-matrix";
import { TrustBreakdown } from "./trust-breakdown";
import { Printer } from "lucide-react";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Badge } from "@/components/shared/status-badge";
import { Title } from "@/components/shared/page-heading";
import { EvidenceSection } from "./evidence-section";
import { Timeline } from "@/components/students/audit-timeline";

export function PassportScreen({
  id,
  print,
  timeline,
}: {
  id: string;
  print: boolean;
  timeline: boolean;
}) {
  const query = useData<Row>("/students/" + id + "?include_evidence=false");
  const data = query.data,
    profile = data?.profile as Row | undefined,
    trust = data?.trust as Row | undefined;
  const printable = Boolean(profile && trust && !query.loading && !query.error);
  if (timeline) return <Timeline id={id} />;
  return (
    <>
      <Title
        title={profile ? text(profile.full_name) : "Academic passport"}
        description="Academic passport"
      >
        {print ? (
          <button disabled={!printable} onClick={() => window.print()}>
            <Printer size={16} /> Print passport
          </button>
        ) : printable ? (
          <Link className="button" href={"/students/" + id + "/print"}>
            <Printer size={16} /> Print passport
          </Link>
        ) : (
          <button disabled>
            <Printer size={16} />
            Print passport
          </button>
        )}
      </Title>
      <State {...query} retry={query.reload}>
        {data && profile && trust ? (
          <>
            <ProfileHeader profile={profile} cgpa={data.cgpa} trust={trust} />
            <nav className="section-nav">
              <a href="#performance">Performance</a>
              <a href="#evidence">Evidence</a>
              <a href="#trust">Trust formula</a>
              <Link href={"/students/" + id + "/timeline"}>Timeline</Link>
            </nav>
            <section className="panel" id="performance">
              <div className="panel-heading">
                <div>
                  <h2>Performance by term</h2>
                </div>
                <Badge value={profile.data_quality_status} />
              </div>
              <TermMatrix profile={profile} terms={data.terms as Row[]} />
            </section>
            <div id="evidence">
              {[
                "certificates",
                "projects",
                "internships",
                "achievements",
                "scholarships",
                "skills",
              ].map((key) => (
                <RemoteEvidence
                  key={key}
                  id={id}
                  section={key}
                  title={key[0].toUpperCase() + key.slice(1)}
                  columns={
                    EVIDENCE_COLUMNS[key] || [
                      ["title", "Title"],
                      ["description", "Description"],
                    ]
                  }
                />
              ))}
            </div>
            <TrustBreakdown trust={trust} />
          </>
        ) : null}
      </State>
    </>
  );
}

function RemoteEvidence({
  id,
  section,
  title,
  columns,
}: {
  id: string;
  section: string;
  title: string;
  columns: [string, string][];
}) {
  const query = useData<{ items: Row[] }>(
    "/students/" + id + "/evidence/" + section,
  );
  if (query.loading)
    return (
      <section className="panel padded" aria-busy="true">
        <h2>{title}</h2>
        <p>Loading evidence…</p>
      </section>
    );
  return (
    <EvidenceSection
      title={title}
      rows={query.error ? undefined : query.data?.items}
      columns={columns}
      onRetry={query.reload}
    />
  );
}

const EVIDENCE_COLUMNS: Record<string, [string, string][]> = {
  certificates: [
    ["title", "Certificate"],
    ["issuer", "Issuer"],
    ["purpose", "Purpose"],
    ["acceptance_status", "Acceptance"],
  ],
  skills: [
    ["label", "Skill"],
    ["proficiency", "Proficiency / 5"],
    ["evidence_kind", "Evidence"],
  ],
  internships: [
    ["organization", "Organization"],
    ["role", "Role"],
    ["start_date", "Started"],
  ],
  scholarships: [
    ["name", "Scholarship"],
    ["academic_year", "Year"],
    ["amount_inr", "Amount INR"],
  ],
};

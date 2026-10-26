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
  const query = useData<Row>("/students/" + id);
  const data = query.data,
    profile = data?.profile as Row | undefined,
    trust = data?.trust as Row | undefined;
  const printable = Boolean(profile && trust && !query.loading && !query.error);
  if (timeline) return <Timeline id={id} />;
  return (
    <>
      <Title
        eyebrow="ACADEMIC PASSPORT"
        title={profile ? text(profile.full_name) : "Academic passport"}
        description="Synthetic academic history · Local consistency, never official verification"
      >
        {printable ? (
          <Link className="button" href={"/students/" + id + "/print"}>
            <Printer size={16} /> Print passport
          </Link>
        ) : (
          <button disabled>
            <Printer size={16} />
            Print passport
          </button>
        )}
        {print ? (
          <button disabled={!printable} onClick={() => window.print()}>
            Open print preview
          </button>
        ) : null}
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
                  <div className="eyebrow">ACADEMIC LEDGER</div>
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
                <EvidenceSection
                  key={key}
                  title={key[0].toUpperCase() + key.slice(1)}
                  rows={data[key]}
                  columns={
                    EVIDENCE_COLUMNS[key] || [
                      ["title", "Title"],
                      ["description", "Description"],
                    ]
                  }
                  onRetry={query.reload}
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

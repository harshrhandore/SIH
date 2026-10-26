"use client";
import Link from "next/link";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Badge } from "@/components/shared/status-badge";
import { Title } from "@/components/shared/page-heading";
import { ExtractionPanel } from "./extraction-panel";
import { RiskReasons } from "./risk-reasons";
import { MatchTable } from "./match-table";

export function CertificateReport({ id }: { id: string }) {
  const query = useData<Row>("/certificate-verifications/" + id);
  const d = query.data,
    risk = d?.risk as Row | undefined;
  return (
    <>
      <Title title="Local certificate consistency report" />
      <State {...query} retry={query.reload}>
        {d && risk ? (
          <>
            <div className="notice">
              {d.purpose === "TRIAL"
                ? "Verification trial — excluded from accepted passport and Trust Score"
                : "Passport evidence — staff acceptance is required"}
            </div>
            <div className="metrics report-metrics">
              <div className="metric">
                <span>Local match confidence</span>
                <strong>
                  {Number(d.confidence).toFixed(2)}
                  <small>%</small>
                </strong>
                <Badge value={d.verdict} />
              </div>
              <div className="metric">
                <span>Heuristic risk score</span>
                <strong>
                  {text(risk.score)}
                  <small>/100</small>
                </strong>
                <Badge
                  value={
                    risk.level === "high"
                      ? "HIGH RISK — REVIEW REQUIRED"
                      : risk.level
                  }
                />
              </div>
            </div>
            <ExtractionPanel d={d} />
            <MatchTable matches={d.matches as Row} />
            <RiskReasons d={d} risk={risk} />
            <Link className="button" href="/certificates">
              New trial
            </Link>
          </>
        ) : null}
      </State>
    </>
  );
}

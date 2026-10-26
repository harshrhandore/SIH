"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckCircle2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Badge } from "@/components/shared/status-badge";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { useRequiredUser } from "@/hooks/use-current-user";

export function CaseDetail({ id }: { id: string }) {
  const user = useRequiredUser();
  const [grant, setGrant] = useState("");
  const query = useData<Row>("/cases/" + id, 0, grant);
  const [note, setNote] = useState(""),
    [correction, setCorrection] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const data = query.data,
    caseRow = data?.case as Row | undefined,
    passport = data?.student as Row | undefined,
    profile = passport?.profile as Row | undefined;
  async function decide(action: string) {
    setBusy(true);
    setMessage("");
    try {
      await api("/cases/" + id + "/decisions", {
        method: "POST",
        headers: grant ? { "X-Case-Access": grant } : {},
        body: JSON.stringify({
          expected_version: caseRow?.version_no,
          action,
          reason: note,
          requested_fields:
            action === "REQUEST_CORRECTION" ? ["submitted_apaar_id"] : [],
        }),
      });
      setMessage("Decision recorded.");
      query.reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function correct() {
    setBusy(true);
    try {
      await api("/students/" + caseRow?.student_id, {
        method: "PATCH",
        body: JSON.stringify({
          expected_version: profile?.version_no,
          patch: { submitted_apaar_id: correction },
          reason: note,
        }),
      });
      setMessage("Correction saved. Officer review is required.");
      query.reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="CASE FILE"
        title={profile ? text(profile.full_name) : "Verification case"}
        description={"Case " + id}
      />
      <State {...query} retry={query.reload}>
        {data && caseRow ? (
          <>
            <section className="panel padded">
              <Badge value={caseRow.status} />
              <h2>{text(caseRow.opened_reason).replaceAll("_", " ")}</h2>
              {data.masked ? (
                <div>
                  <p>
                    This case is masked. An administrator can inspect raw
                    details only with a reasoned, case-bound escalation grant.
                  </p>
                  {caseRow.status === "ESCALATED" ? (
                    <>
                      <label>
                        Reason for inspecting this escalated case
                        <textarea
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          maxLength={1000}
                        />
                      </label>
                      <button
                        disabled={note.trim().length < 10 || busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            const r = await api<{
                              access_grant: string;
                            }>("/cases/" + id + "/access", {
                              method: "POST",
                              body: JSON.stringify({ reason: note }),
                            });
                            setGrant(r.access_grant);
                            setTimeout(() => {
                              setGrant("");
                              query.reload();
                            }, 300000);
                          } catch (e) {
                            setMessage((e as Error).message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Record reason and inspect case
                      </button>
                    </>
                  ) : null}
                </div>
              ) : (
                <>
                  <p className="mono">
                    {text(profile?.apaar_id)} · Version{" "}
                    {text(profile?.version_no)}
                  </p>
                  <div className="two-columns">
                    <div>
                      <h3>Current findings</h3>
                      {(data.findings as Row[]).length ? (
                        (data.findings as Row[]).map((f) => (
                          <div className="finding" key={text(f.code)}>
                            <Badge value={f.severity} />
                            <h3>{text(f.code).replaceAll("_", " ")}</h3>
                            <p>{text(f.explanation)}</p>
                          </div>
                        ))
                      ) : (
                        <p>
                          <CheckCircle2 size={17} /> No unresolved findings.
                        </p>
                      )}
                      <h3>Candidate review</h3>
                      <Table
                        rows={data.duplicates as Row[]}
                        columns={[
                          ["match_type", "Type"],
                          ["score", "Score"],
                          ["status", "Status"],
                        ]}
                      />
                    </div>
                    <div className="review-form">
                      <h3>Record the next action</h3>
                      <label>
                        Reason (10–1,000 characters)
                        <textarea
                          minLength={10}
                          maxLength={1000}
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          placeholder="Describe the source evidence and your decision."
                        />
                      </label>
                      {user.role === "OPERATOR" ? (
                        <>
                          <label>
                            Corrected synthetic ID
                            <input
                              value={correction}
                              onChange={(e) => setCorrection(e.target.value)}
                              placeholder="Value from fixtures/manifest.json"
                            />
                          </label>
                          <button
                            className="primary"
                            disabled={
                              note.trim().length < 10 || busy || !correction
                            }
                            onClick={correct}
                          >
                            {busy ? "Saving…" : "Save correction"}
                          </button>
                        </>
                      ) : (
                        (data.allowed_actions as string[]).map((action) => (
                          <button
                            className={action === "APPROVE" ? "primary" : ""}
                            disabled={note.trim().length < 10 || busy}
                            key={action}
                            onClick={() => decide(action)}
                          >
                            {action.replaceAll("_", " ")}
                          </button>
                        ))
                      )}
                      <p className="note">
                        Confirmation never merges student identities.
                      </p>
                    </div>
                  </div>
                  <Link href={"/students/" + caseRow.student_id + "/timeline"}>
                    Open audit timeline <ArrowRight size={15} />
                  </Link>
                </>
              )}
              {message ? (
                <p role="status" className="notice">
                  {message}
                </p>
              ) : null}
            </section>
            {data.versions ? (
              <section className="panel">
                <div className="panel-heading">
                  <h2>Immutable version history</h2>
                </div>
                <Table
                  rows={data.versions as Row[]}
                  columns={[
                    ["version_no", "Version"],
                    ["reason", "Reason"],
                    ["created_at", "Created"],
                  ]}
                />
              </section>
            ) : null}
          </>
        ) : null}
      </State>
    </>
  );
}

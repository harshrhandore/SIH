"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { Envelope } from "@/lib/schemas";
import { text } from "@/lib/format";
import { useData } from "@/hooks/use-data";
import { State } from "@/components/shared/view-state";
import { Title } from "@/components/shared/page-heading";
import { Table } from "@/components/shared/data-table";
import { useRequiredUser } from "@/hooks/use-current-user";

export function DemoControls() {
  const user = useRequiredUser();
  const query = useData<Row>("/demo/config");
  const institutions = useData<Envelope>(
    user.role === "STUDENT" ? null : "/institutions",
  );
  const [institution, setInstitution] = useState(
    user.institution_id || user.assigned_institutions[0] || "",
  );
  const [result, setResult] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const benchmark = useData<Row>(
    runId ? "/demo/benchmarks/" + runId : null,
    runId ? 1000 : 0,
  );
  async function verifyChain(copy: boolean) {
    setPending(true);
    setError("");
    try {
      setResult(
        await api<Row>(
          (copy ? "/demo/audit-sandbox/verify" : "/audit/verify-chain") +
            "?institution_id=" +
            institution,
        ),
      );
    } catch (e) {
      setResult(null);
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Title
        title="Demo controls"
        description="Actual capabilities and owner-only commands."
      />
      <section className="panel padded">
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <Table
                rows={Object.entries(query.data).map(([capability, value]) => ({
                  capability,
                  value,
                }))}
                columns={[
                  ["capability", "Capability"],
                  ["value", "Current state"],
                ]}
              />
              {user.role !== "STUDENT" ? (
                <>
                  <label>
                    Institution for audit verification
                    <select
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                    >
                      <option value="">Choose an institution</option>
                      {institutions.data?.items.map((row) => (
                        <option key={text(row.id)} value={text(row.id)}>
                          {text(row.name)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="heading-actions">
                    <button
                      disabled={!institution || pending}
                      onClick={() => verifyChain(true)}
                    >
                      Verify isolated copy
                    </button>
                    <button
                      disabled={!institution || pending}
                      onClick={() => verifyChain(false)}
                    >
                      Verify production chain
                    </button>
                  </div>
                  {error ? (
                    <p className="error" role="alert">
                      {error}
                    </p>
                  ) : null}
                  {result ? (
                    <div
                      className={result.valid ? "notice" : "error"}
                      role="status"
                    >
                      <strong>
                        {result.is_copy ? "Isolated copy" : "Production chain"}:{" "}
                        {result.valid ? "valid" : "broken"}
                      </strong>
                      <span>
                        {result.first_broken_link
                          ? JSON.stringify(result.first_broken_link)
                          : "Full chain verified through head " +
                            text(result.head_seq)}
                      </span>
                      {result.is_copy ? (
                        <p>Isolated copy · production chain unchanged</p>
                      ) : null}
                    </div>
                  ) : null}
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={query.data.cache_enabled_for_session !== false}
                      onChange={async (e) => {
                        try {
                          await api("/demo/session-controls", {
                            method: "PUT",
                            body: JSON.stringify({
                              cache_enabled: e.target.checked,
                            }),
                          });
                          query.reload();
                        } catch (e) {
                          setError((e as Error).message);
                        }
                      }}
                    />{" "}
                    Use the application result cache for this session
                  </label>
                  {["ADMIN", "OFFICER"].includes(user.role) ? (
                    <>
                      <h2>Measured search performance</h2>
                      <button
                        disabled={
                          pending || benchmark.data?.status === "RUNNING"
                        }
                        onClick={async () => {
                          setPending(true);
                          setError("");
                          try {
                            const run = await api<{
                              run_id: string;
                            }>("/demo/benchmarks", {
                              method: "POST",
                              body: JSON.stringify({
                                dataset: "current",
                                runs: 20,
                                cache_mode: "BOTH",
                              }),
                            });
                            setRunId(run.run_id);
                          } catch (e) {
                            setError((e as Error).message);
                          } finally {
                            setPending(false);
                          }
                        }}
                      >
                        Run 20-query benchmark
                      </button>
                      {benchmark.data ? (
                        <>
                          <p role="status">
                            Benchmark{" "}
                            {text(benchmark.data.status).toLowerCase()}
                          </p>
                          {benchmark.data.result ? (
                            <pre>
                              {JSON.stringify(benchmark.data.result, null, 2)}
                            </pre>
                          ) : null}
                        </>
                      ) : null}
                    </>
                  ) : null}
                </>
              ) : null}
              <h2>Local CLI required</h2>
              <p>
                Audit sandbox writes run with owner credentials in your
                terminal. Web processes have no owner credentials or sandbox
                privileges.
              </p>
              <pre>
                python -m app.cli audit-sandbox create --institution-key
                institution_a
              </pre>
              <pre>
                python -m app.cli audit-sandbox tamper --institution-key
                institution_a
              </pre>
              <p>
                Read MORNING.md for environment limits and unverified gates.
              </p>
              <p className="note">
                Current role: {user.role}. No HTTP reset or tamper-write
                endpoint exists.
              </p>
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}

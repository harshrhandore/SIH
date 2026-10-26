"use client";
import { useState } from "react";
import { GraduationCap } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { kolkataDateTime } from "@/lib/format";
import type { components } from "@/lib/generated/api";
import { Title } from "@/components/shared/page-heading";
import { State } from "@/components/shared/view-state";
import { useRequiredUser } from "@/hooks/use-current-user";
import { useData } from "@/hooks/use-data";
import { QuestionBox } from "./question-box";
import { ReadinessPanel } from "./readiness-panel";
import { StepsList } from "./steps-list";

type Advice = components["schemas"]["CareerResponse"];
export function CareerScreen() {
  const user = useRequiredUser();
  const [question, setQuestion] = useState("Can I become a Data Scientist?");
  const [role, setRole] = useState("");
  const [result, setResult] = useState<Advice | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [historySize, setHistorySize] = useState(25);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const roles = useData<components["schemas"]["RolesResponse"]>(
    user.role === "STUDENT" ? "/career/roles" : null,
  );
  const history = useData<components["schemas"]["HistoryResponse"]>(
    user.role === "STUDENT"
      ? "/students/" +
          user.student_id +
          "/career/history?page=" +
          historyPage +
          "&page_size=" +
          historySize
      : null,
  );
  async function send() {
    setBusy(true);
    setError(null);
    try {
      const saved = await api<Advice>(
        "/students/" + user.student_id + "/career",
        {
          method: "POST",
          body: JSON.stringify({
            question,
            ...(role ? { role_code: role } : {}),
          }),
        },
      );
      setResult(saved);
      setSavedAt(null);
      setHistoryPage(1);
      await history.reload();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setBusy(false);
    }
  }
  if (user.role !== "STUDENT")
    return (
      <div className="empty">
        <h1>Student view</h1>
        <p>Career guidance is available to the student account.</p>
      </div>
    );
  return (
    <>
      <Title
        eyebrow="EVIDENCE-BASED NEXT STEPS"
        title="Career Copilot"
        description="A deterministic readiness score. Practical steps based on the evidence you have."
      />
      <div className="two-columns career-layout">
        <section className="panel padded">
          <QuestionBox
            question={question}
            role={role}
            roles={roles.data?.roles || []}
            busy={busy}
            error={error}
            onQuestion={setQuestion}
            onRole={setRole}
            onSend={send}
          />
          {roles.error ? (
            <p role="alert">
              {roles.error.message}{" "}
              <button onClick={roles.reload}>Retry roles</button>
            </p>
          ) : null}
          {result ? (
            <>
              <div className="notice" role="status">
                {savedAt
                  ? "Saved advice from " + kolkataDateTime(savedAt)
                  : "Deterministic score"}{" "}
                &middot; {result.phrasing_source}
              </div>
              <p>{result.explanation}</p>
              <StepsList steps={result.recommended_steps} />
            </>
          ) : (
            <div className="empty">
              <GraduationCap />
              <p>Your evidence and next steps will appear here.</p>
            </div>
          )}
        </section>
        <ReadinessPanel result={result} />
      </div>
      <section className="panel padded" id="saved-advice" tabIndex={-1}>
        <h2>Saved advice</h2>
        <label>
          Advice per page
          <select
            value={historySize}
            onChange={(event) => {
              setHistorySize(Number(event.target.value));
              setHistoryPage(1);
            }}
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </label>
        <State {...history} retry={history.reload}>
          {history.data?.items.length ? (
            <ul className="advice-history">
              {history.data.items.map((item) => (
                <li key={item.session_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setQuestion(item.question);
                      setRole(item.role_code);
                      setSavedAt(item.created_at);
                      setResult({
                        ...item.response,
                        session_id: item.session_id,
                      });
                      setError(null);
                    }}
                  >
                    {item.question} &middot; {item.readiness_percent}%{" "}
                    <small>{kolkataDateTime(item.created_at)}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              No saved advice yet. Send a question to create your first entry.
            </p>
          )}
        </State>
        {history.data ? (
          <div className="pagination">
            <button
              disabled={historyPage === 1}
              onClick={() => setHistoryPage(historyPage - 1)}
            >
              Previous advice
            </button>
            <span>
              Page {historyPage} &middot; {history.data.total} saved entries
            </span>
            <button
              disabled={historyPage * historySize >= history.data.total}
              onClick={() => setHistoryPage(historyPage + 1)}
            >
              Next advice
            </button>
          </div>
        ) : null}
      </section>
    </>
  );
}

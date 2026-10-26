"use client";
import { ArrowRight } from "lucide-react";
import type { ApiError } from "@/lib/api";
import type { components } from "@/lib/generated/api";

export function QuestionBox({
  question,
  role,
  roles,
  busy,
  error,
  onQuestion,
  onRole,
  onSend,
}: {
  question: string;
  role: string;
  roles: components["schemas"]["Role"][];
  busy: boolean;
  error: ApiError | null;
  onQuestion: (value: string) => void;
  onRole: (value: string) => void;
  onSend: () => void;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSend();
      }}
    >
      <h2>Where do you want to go?</h2>
      <p className="muted">
        Choose a supported role or ask about one role in your question.
      </p>
      <fieldset className="role-chips" disabled={busy}>
        <legend>Target role</legend>
        {roles.map((item) => (
          <label className="role-chip" key={item.code}>
            <input
              type="radio"
              name="career-role"
              value={item.code}
              checked={role === item.code}
              onChange={() => onRole(item.code)}
            />
            {item.label}
          </label>
        ))}
        <button type="button" aria-pressed={!role} onClick={() => onRole("")}>
          Infer from question
        </button>
      </fieldset>
      <label>
        Your question
        <textarea
          value={question}
          onChange={(event) => onQuestion(event.target.value)}
          maxLength={1000}
          disabled={busy}
        />
      </label>
      <button
        className="primary"
        disabled={busy || !question.trim()}
        type="submit"
      >
        {busy ? "Comparing evidence…" : "Send question"}
        <ArrowRight size={16} />
      </button>
      {error ? (
        <div className="error" role="alert">
          <p>{error.message}</p>
          <small>{error.requestId}</small>
          {error.code === "UNKNOWN_CAREER_ROLE" ? (
            <p>
              Choose a supported role above, or ask about one role at a time.
            </p>
          ) : null}
          {error.code === "RATE_LIMITED" ? (
            <p>
              Please wait before sending another question.{" "}
              <a href="#saved-advice">Open saved advice</a> while you wait.
            </p>
          ) : null}
        </div>
      ) : null}
    </form>
  );
}

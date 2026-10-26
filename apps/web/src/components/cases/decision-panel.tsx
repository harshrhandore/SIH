"use client";
export function DecisionPanel({
  role,
  note,
  setNote,
  correction,
  setCorrection,
  busy,
  correct,
  decide,
  allowedActions,
}: {
  role: string;
  note: string;
  setNote: (value: string) => void;
  correction: string;
  setCorrection: (value: string) => void;
  busy: boolean;
  correct: () => void;
  decide: (action: string) => void;
  allowedActions: string[];
}) {
  return (
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
      {role === "OPERATOR" ? (
        <>
          <label>
            Corrected synthetic ID
            <input
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
              placeholder="Enter the corrected identifier…"
            />
          </label>
          <button
            className="primary"
            disabled={note.trim().length < 10 || busy || !correction}
            onClick={correct}
          >
            {busy ? "Saving…" : "Save correction"}
          </button>
        </>
      ) : (
        allowedActions.map((action) => (
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
      <p className="note">Confirmation never merges student identities.</p>
    </div>
  );
}

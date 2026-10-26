"use client";
import { useState } from "react";
import type { Row } from "@/lib/schemas";
import { text } from "@/lib/format";
import { api } from "@/lib/api";
import { Table } from "@/components/shared/data-table";
import { ReasonDialog } from "@/components/shared/reason-dialog";

export function CandidatePanel({
  rows,
  caseRow,
  canDecide,
  grant,
  onSaved,
}: {
  rows: Row[];
  caseRow: Row;
  canDecide: boolean;
  grant: string;
  onSaved: () => void;
}) {
  const [selected, setSelected] = useState<{
    id: string;
    action: string;
  } | null>(null);
  const [message, setMessage] = useState("");
  return (
    <section>
      <h3>Candidate review</h3>
      <Table
        rows={rows}
        columns={[
          ["match_type", "Type"],
          ["score", "Score"],
          ["status", "Status"],
        ]}
      />
      {canDecide &&
        rows.map((row, index) => (
          <div key={text(row.id)}>
            <p>Candidate {index + 1}</p>
            {(["DISMISS_DUPLICATE", "CONFIRM_DUPLICATE"] as const).map(
              (action) => (
                <button
                  key={action}
                  onClick={() => setSelected({ id: text(row.id), action })}
                >
                  {action === "DISMISS_DUPLICATE"
                    ? "Dismiss candidate"
                    : "Confirm duplicate"}
                </button>
              ),
            )}
          </div>
        ))}
      {message ? <p role="status">{message}</p> : null}
      {selected ? (
        <ReasonDialog
          title={selected.action.replaceAll("_", " ")}
          onClose={() => setSelected(null)}
          onConfirm={async (reason) => {
            await api("/duplicate-candidates/" + selected.id + "/decision", {
              method: "POST",
              headers: grant ? { "X-Case-Access": grant } : {},
              body: JSON.stringify({
                action: selected.action,
                case_id: caseRow.id,
                expected_case_version: caseRow.version_no,
                reason,
              }),
            });
            setMessage(
              "Candidate decision recorded. Student identities were not merged.",
            );
            onSaved();
          }}
        />
      ) : null}
    </section>
  );
}

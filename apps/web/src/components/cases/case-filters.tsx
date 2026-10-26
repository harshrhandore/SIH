"use client";
export function CaseFilters({
  status,
  q,
  setStatus,
  setQ,
}: {
  status: string;
  q: string;
  setStatus: (value: string) => void;
  setQ: (value: string) => void;
}) {
  return (
    <div className="filters">
      <label>
        Case status
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {["OPEN", "CORRECTION_REQUESTED", "ESCALATED", "APPROVED", ""].map(
            (v) => (
              <option key={v} value={v}>
                {v ? v.toLowerCase().replaceAll("_", " ") : "All statuses"}
              </option>
            ),
          )}
        </select>
      </label>
      <label>
        Enrollment or name
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="DEMO-A-0032"
        />
      </label>
    </div>
  );
}

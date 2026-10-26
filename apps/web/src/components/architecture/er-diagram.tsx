const relationships = {
  "Core ER": [
    ["Institutions", "Programs", "1:N"],
    ["Institutions", "Students", "1:N"],
    ["Programs", "Expected records", "1:1"],
    ["Students", "Enrolments", "1:N"],
    ["Enrolments", "Term performance", "1:N"],
  ],
  "Governance ER": [
    ["Students", "Cases", "1:N"],
    ["Cases", "Decisions", "1:N"],
    ["Students", "Record versions", "1:N"],
    ["Audit chains", "Audit events", "1:N"],
    ["Users", "Institutions", "N:M"],
  ],
  "AI ER": [
    ["Students", "Certificates", "1:N"],
    ["Certificates", "Verifications", "1:N"],
    ["Students", "Skills", "N:M"],
    ["Students", "Career sessions", "1:N"],
    ["Students", "Trust score", "1:1"],
  ],
} as const;

export function ERDiagram({ group }: { group: keyof typeof relationships }) {
  return (
    <svg
      role="img"
      aria-label={group + " entity relationships"}
      viewBox="0 0 720 400"
      style={{ width: "100%", minWidth: 280 }}
    >
      <title>{group}</title>
      {relationships[group].map(([left, right, cardinality], index) => (
        <g key={left + right} transform={`translate(0 ${index * 78})`}>
          <rect
            x="5"
            y="5"
            width="230"
            height="54"
            rx="6"
            fill="var(--surface)"
            stroke="currentColor"
          />
          <text x="120" y="37" textAnchor="middle" fill="currentColor">
            {left}
          </text>
          <line x1="235" y1="32" x2="485" y2="32" stroke="currentColor" />
          <rect x="320" y="15" width="80" height="30" fill="var(--paper)" />
          <text x="360" y="37" textAnchor="middle" fill="currentColor">
            {cardinality}
          </text>
          <rect
            x="485"
            y="5"
            width="230"
            height="54"
            rx="6"
            fill="var(--surface)"
            stroke="currentColor"
          />
          <text x="600" y="37" textAnchor="middle" fill="currentColor">
            {right}
          </text>
        </g>
      ))}
    </svg>
  );
}

import { Table } from "@/components/shared/data-table";
import type { components } from "@/lib/generated/api";

export function ReadinessPanel({
  result,
}: {
  result: components["schemas"]["CareerResponse"] | null;
}) {
  return (
    <section className="panel padded">
      <h2>Skills match</h2>
      <div className="readiness">
        {result?.readiness_percent ?? "—"}
        <small>%</small>
      </div>
      <p>Match against required skills, out of 100.</p>
      {result ? (
        <>
          <h3>Matched skills</h3>
          <Table
            rows={result.matched_skills.map((skill) => ({
              label: skill.label,
              weight: skill.weight,
              evidence: skill.evidence
                .map((item) => `${item.kind}: ${item.title || item.id}`)
                .join(" · "),
            }))}
            columns={[
              ["label", "Skill"],
              ["weight", "Points"],
              ["evidence", "Qualifying evidence"],
            ]}
          />
          <h3>Missing evidence</h3>
          <Table
            rows={result.missing_skills.map((skill) => ({
              label: skill.label,
              weight: skill.weight,
            }))}
            columns={[
              ["label", "Skill"],
              ["weight", "Points"],
            ]}
          />
          <h3>Suggested learning</h3>
          <ul>
            {result.suggested_courses.map((course) => (
              <li key={course.title}>
                {course.title} · {course.provider}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="note">
        Only skills supported by recorded evidence contribute to this score.
      </p>
    </section>
  );
}

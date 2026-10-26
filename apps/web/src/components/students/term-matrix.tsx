import { Table } from "@/components/shared/data-table";
import type { Row } from "@/lib/schemas";

export function TermMatrix({ profile, terms }: { profile: Row; terms: Row[] }) {
  const total = Number(profile.total_terms || 0);
  if (!total)
    return (
      <div className="empty">
        <p>A program structure is required to display the term matrix.</p>
      </div>
    );
  const byTerm = new Map(terms.map((term) => [Number(term.term_no), term]));
  const perYear = profile.term_type === "TRIMESTER" ? 3 : 2;
  const rows = Array.from({ length: total }, (_, index) => {
    const term = byTerm.get(index + 1);
    return {
      id: index + 1,
      term: `${profile.term_type === "TRIMESTER" ? "Trimester" : "Semester"} ${index + 1}`,
      academic_year:
        term?.academic_year ??
        (profile.admission_year
          ? Number(profile.admission_year) + Math.floor(index / perYear)
          : null),
      credits: term?.credits ?? null,
      sgpa:
        term?.sgpa === undefined || term.sgpa === null
          ? null
          : Number(term.sgpa).toFixed(2),
      cgpa:
        term?.cgpa === undefined || term.cgpa === null
          ? null
          : Number(term.cgpa).toFixed(2),
      result: term
        ? Number(term.sgpa) >= 4
          ? "Pass"
          : "Below pass mark"
        : "Not completed",
    };
  });
  return (
    <Table
      rows={rows}
      columns={[
        ["term", "Term"],
        ["academic_year", "Academic year"],
        ["credits", "Credits"],
        ["sgpa", "SGPA"],
        ["cgpa", "Cumulative CGPA"],
        ["result", "Result"],
      ]}
    />
  );
}

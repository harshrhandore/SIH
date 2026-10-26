import type { Row } from "@/lib/schemas";
import { Table } from "@/components/shared/data-table";
export function RiskReasons({ d, risk }: { d: Row; risk: Row }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Heuristic risk signals</h2>
        <span>Heuristic, not validated</span>
      </div>
      <Table
        rows={risk.reasons as Row[]}
        columns={[
          ["label", "Reason"],
          ["weight", "Weight"],
          ["evidence", "Measured evidence"],
        ]}
      />
      <div className="padded">
        <h3>Not assessed</h3>
        <p>{(d.not_assessed as string[]).join(" · ")}</p>
        <p>{(d.warnings as string[]).join(" ")}</p>
      </div>
    </section>
  );
}

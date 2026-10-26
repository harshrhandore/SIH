import { Table } from "@/components/shared/data-table";
import { text } from "@/lib/format";
import type { Row } from "@/lib/schemas";

export function TrustBreakdown({ trust }: { trust: Row }) {
  return (
    <section className="panel" id="trust">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">HEURISTIC, NOT VALIDATED</div>
          <h2>Trust Score · {text(trust.score)} / 100</h2>
        </div>
        <span>Formula version {text(trust.formula_version)}</span>
      </div>
      <Table
        rows={trust.components as Row[]}
        columns={[
          ["key", "Component"],
          ["earned", "Earned"],
          ["max", "Maximum"],
          ["reason", "Explanation"],
        ]}
      />
      <p className="note padded">
        Mock verification adds zero official points. Trial certificates are
        excluded. Scores are computed from synthetic fixtures calibrated for
        this demonstration.
      </p>
    </section>
  );
}

import { Table } from "@/components/shared/data-table";
import { text } from "@/lib/format";
import type { Row } from "@/lib/schemas";

export function TrustBreakdown({ trust }: { trust: Row }) {
  return (
    <section className="panel" id="trust">
      <div className="panel-heading">
        <div>
          <h2>Trust Score · {text(trust.score)} / 100</h2>
        </div>
        <span className="note">Heuristic, not validated</span>
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
        Based on the recorded evidence below. Trial certificates and mock
        verification add no official verification credit.
      </p>
    </section>
  );
}

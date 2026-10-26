import { Badge } from "@/components/shared/status-badge";
import { text } from "@/lib/format";
import type { Row } from "@/lib/schemas";

export function ProfileHeader({
  profile,
  cgpa,
  trust,
}: {
  profile: Row;
  cgpa: unknown;
  trust: Row;
}) {
  return (
    <section className="passport-header panel padded">
      <div className="passport-identity">
        <div>
          <p className="institution-name">{text(profile.institution_name)}</p>
          <h2>{text(profile.program)}</h2>
          <p className="mono">{text(profile.apaar_id)}</p>
          <Badge value={profile.external_status} />
        </div>
      </div>
      <div className="passport-number">
        <span>CGPA</span>
        <strong>{text(cgpa)}</strong>
        <small>Credit-weighted · / 10</small>
      </div>
      <div className="passport-number">
        <span>Trust score</span>
        <strong>{text(trust.score)}</strong>
        <small>Heuristic score / 100</small>
      </div>
    </section>
  );
}

import Image from "next/image";
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
        <Image
          src="/seal.svg"
          alt="Synthetic academic ledger seal"
          width={60}
          height={60}
        />
        <div>
          <div className="eyebrow">{text(profile.institution_name)}</div>
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
      <div className="trust-ring">
        <strong>{text(trust.score)}</strong>
        <span>Trust / 100</span>
      </div>
    </section>
  );
}

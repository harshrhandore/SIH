import { ShieldCheck } from "lucide-react";

export function GlobalBanner() {
  return (
    <div className="global-synthetic-banner">
      SYNTHETIC DATA &middot; Not an official APAAR service
    </div>
  );
}

export function ScopeBanner() {
  return (
    <div className="scope-strip">
      <ShieldCheck size={14} /> Synthetic demonstration{" "}
      <span>
        Local checks and mock results are distinct from official verification.
      </span>
    </div>
  );
}

"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ShieldCheck, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { Title } from "@/components/shared/page-heading";
import { useRequiredUser } from "@/hooks/use-current-user";

export function CertificateUpload() {
  const user = useRequiredUser();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null),
    [purpose, setPurpose] = useState("TRIAL"),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  async function verify() {
    if (!file) return;
    setBusy(true);
    setMessage("Saving file and computing local consistency…");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("purpose", purpose);
      form.set("title", "Synthetic supporting certificate");
      const uploaded = await api<Row>(
        "/students/" + user.student_id + "/certificates",
        { method: "POST", body: form },
      );
      setMessage("Reading text and comparing with the synthetic record…");
      const report = await api<Row>(
        "/certificates/" + uploaded.certificate_id + "/verify",
        { method: "POST", body: "{}" },
      );
      router.push("/certificates/" + report.verification_id);
    } catch (e) {
      setMessage((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="EXPLAINABLE EVIDENCE"
        title="Certificates"
        description="Check document consistency against your synthetic academic record."
      />
      <section className="panel padded">
        <div className="notice">
          Local consistency checks are not issuer authentication or official
          verification.
        </div>
        <div className="fixture-links">
          <a href="/api/backend/demo/fixtures/genuine_pdf" download>
            Genuine PDF fixture
          </a>
          <a href="/api/backend/demo/fixtures/tampered_pdf" download>
            Tampered PDF fixture
          </a>
          <a href="/api/backend/demo/fixtures/genuine_png" download>
            PNG OCR fixture
          </a>
        </div>
        <label>
          Purpose
          <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
            <option value="TRIAL">
              Trial — excluded from accepted passport and Trust Score
            </option>
            <option value="PASSPORT">
              Passport — requires staff acceptance
            </option>
          </select>
        </label>
        <label className="dropzone">
          <FileText size={32} />
          <span>{file?.name || "Choose PDF, PNG or JPEG"}</span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <p className="note">
          10 MiB maximum · 10 PDF pages · encrypted or active PDFs rejected
        </p>
        <button className="primary" disabled={!file || busy} onClick={verify}>
          {busy ? "Verifying…" : "Verify local consistency"}
          <ShieldCheck size={16} />
        </button>
        <p role="status">{message}</p>
      </section>
    </>
  );
}

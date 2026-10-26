"use client";
import { UploadStep } from "./upload-step";
import { MappingStep } from "./mapping-step";
import { PreviewStep } from "./preview-step";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Row } from "@/lib/schemas";
import { Title } from "@/components/shared/page-heading";
import { useRequiredUser } from "@/hooks/use-current-user";

export function ImportWizard() {
  const user = useRequiredUser();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null),
    [confirmed, setConfirmed] = useState(false),
    [batch, setBatch] = useState<Row | null>(null),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [preview, setPreview] = useState<Row[] | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function upload() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("institution_id", user.institution_id || "");
      const result = await api<Row>("/imports", { method: "POST", body: form });
      setBatch(result);
      const suggested = result.suggested_mapping as Record<
        string,
        {
          column: string;
        }
      >;
      setMapping(
        Object.fromEntries(
          Object.entries(suggested).map(([k, v]) => [k, v.column]),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function map() {
    setBusy(true);
    setError("");
    try {
      const result = await api<Row>(
        "/imports/" + batch?.batch_id + "/mapping",
        {
          method: "PUT",
          body: JSON.stringify({
            mapping: Object.fromEntries(
              Object.entries(mapping).filter(([, v]) => v),
            ),
            date_format: "DD/MM/YYYY",
          }),
        },
      );
      setPreview(result.preview as Row[]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function validate() {
    setBusy(true);
    try {
      await api("/imports/" + batch?.batch_id + "/validate", {
        method: "POST",
        body: JSON.stringify({ confirm_synthetic_data: confirmed }),
      });
      router.push("/imports/" + batch?.batch_id);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        title="Import synthetic records"
        description="Upload a file, check its columns and validate the records."
      />
      <ol className="steps">
        {["Upload", "Map", "Preview", "Validate", "Report"].map((s, i) => (
          <li
            className={(preview ? 2 : batch ? 1 : 0) === i ? "current" : ""}
            key={s}
          >
            <span>{i + 1}</span>
            {s}
          </li>
        ))}
      </ol>
      <section className="panel padded">
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
        {!batch ? (
          <UploadStep
            file={file}
            confirmed={confirmed}
            busy={busy}
            setFile={setFile}
            setConfirmed={setConfirmed}
            upload={upload}
          />
        ) : !preview ? (
          <MappingStep
            batch={batch}
            mapping={mapping}
            busy={busy}
            setMapping={setMapping}
            map={map}
          />
        ) : (
          <PreviewStep
            preview={preview}
            batch={batch}
            busy={busy}
            validate={validate}
          />
        )}
      </section>
    </>
  );
}

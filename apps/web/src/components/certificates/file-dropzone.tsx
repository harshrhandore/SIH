"use client";
import { FileText } from "lucide-react";
export function FileDropzone({
  file,
  setFile,
}: {
  file: File | null;
  setFile: (file: File | null) => void;
}) {
  return (
    <label className="dropzone">
      <FileText size={32} />
      <span>{file?.name || "Choose PDF, PNG or JPEG"}</span>
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
    </label>
  );
}

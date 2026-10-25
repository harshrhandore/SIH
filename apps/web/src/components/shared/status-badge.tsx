"use client";
import { CheckCircle2, Clock3, AlertTriangle } from "lucide-react";
import { text } from "@/lib/format";

export function Badge({ value }: { value: unknown }) {
  const v = text(value);
  const ok =
    v.includes("PASSED") ||
    v === "APPROVED" ||
    v === "ACCEPTED" ||
    v === "VERIFIED_LOCAL" ||
    v === "COMPLETED";
  const pending = v.includes("PENDING");
  return (
    <span
      className={
        "badge " +
        (ok
          ? "ok"
          : pending
            ? "pending"
            : v === "INCOMPLETE"
              ? "neutral"
              : "warn")
      }
    >
      {ok ? (
        <CheckCircle2 size={13} />
      ) : pending ? (
        <Clock3 size={13} />
      ) : (
        <AlertTriangle size={13} />
      )}{" "}
      {v.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}

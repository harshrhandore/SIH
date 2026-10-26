"use client";
import { useRequiredUser } from "./use-current-user";
import { useData } from "./use-data";
import type { Row } from "@/lib/schemas";

export function useLiveDashboard() {
  const user = useRequiredUser();
  const institution =
    user.role === "OFFICER"
      ? user.assigned_institutions[0]
      : user.institution_id;
  return useData<Row>(
    institution ? "/dashboard?institution_id=" + institution : null,
    5000,
  );
}

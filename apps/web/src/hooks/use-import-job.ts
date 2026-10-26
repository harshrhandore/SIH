"use client";
import { useData } from "./use-data";
import type { Row } from "@/lib/schemas";

export function useImportJob(batchId: string) {
  return useData<Row>("/imports/" + batchId, (data) => {
    if (!data) return 1000;
    return ["QUEUED", "RUNNING"].includes(String(data.status)) ? 1000 : false;
  });
}

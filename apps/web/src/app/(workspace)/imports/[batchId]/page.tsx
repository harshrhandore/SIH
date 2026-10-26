import { ImportDetail } from "@/components/imports/report-step";
export default async function Page({
  params,
}: {
  params: Promise<{ batchId: string }>;
}) {
  const { batchId } = await params;
  return <ImportDetail id={batchId} />;
}

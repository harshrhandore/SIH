import { Timeline } from "@/components/students/audit-timeline";
export default async function Page({
  params,
}: {
  params: Promise<{ studentId: string }>;
}) {
  const { studentId } = await params;
  return <Timeline id={studentId} />;
}

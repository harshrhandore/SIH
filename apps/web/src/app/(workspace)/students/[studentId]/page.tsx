import { PassportScreen } from "@/components/students/passport-sections";
export default async function Page({
  params,
}: {
  params: Promise<{ studentId: string }>;
}) {
  const { studentId } = await params;
  return <PassportScreen id={studentId} print={false} timeline={false} />;
}

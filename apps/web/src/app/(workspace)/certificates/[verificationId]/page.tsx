import { CertificateReport } from "@/components/certificates/report-screen";
export default async function Page({
  params,
}: {
  params: Promise<{ verificationId: string }>;
}) {
  const { verificationId } = await params;
  return <CertificateReport id={verificationId} />;
}

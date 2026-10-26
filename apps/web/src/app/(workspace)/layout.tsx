import { Suspense } from "react";
import { Providers } from "@/app/providers";
import { AppShell } from "@/components/shell/app-shell";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <Suspense
        fallback={
          <main className="boot" role="status">
            Opening workspace…
          </main>
        }
      >
        <AppShell>{children}</AppShell>
      </Suspense>
    </Providers>
  );
}

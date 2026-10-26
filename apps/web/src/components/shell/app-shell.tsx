"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useCallback } from "react";
import { useCurrentUser } from "@/hooks/use-current-user";
import { State } from "@/components/shared/view-state";
import { ScopeBanner } from "@/components/shared/scope-banner";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const session = useCurrentUser();
  const [mobile, setMobile] = useState(false);
  const closeMobile = useCallback(() => setMobile(false), []);
  const user = session.data;
  if (!user)
    return (
      <main className="boot">
        <State {...session} retry={session.reload}>
          <Link href="/login">Sign in to open the ledger</Link>
        </State>
      </main>
    );
  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        path={path}
        mobile={mobile}
        onNavigate={closeMobile}
      />
      <div className="workspace">
        <Topbar
          user={user}
          path={path}
          mobile={mobile}
          onToggle={() => setMobile(!mobile)}
        />
        <ScopeBanner />
        <main className="content">{children}</main>
        <footer className="footer">
          SHIKSHAM APAAR{" "}
          <span>Evidence you can inspect. Decisions you can trace.</span>
          <span>SYNTHETIC PROTOTYPE</span>
        </footer>
      </div>
    </div>
  );
}

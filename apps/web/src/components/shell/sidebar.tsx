"use client";

import Link from "next/link";
import { BookOpen, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { NAVIGATION } from "@/lib/constants";
import { homeFor } from "@/lib/auth";
import type { User } from "@/lib/schemas";

export function Sidebar({
  user,
  path,
  mobile,
  onNavigate,
}: {
  user: User;
  path: string;
  mobile: boolean;
  onNavigate: () => void;
}) {
  const sidebar = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!mobile || !sidebar.current) return;
    const panel = sidebar.current;
    const previous = document.activeElement as HTMLElement | null;
    const background =
      panel.parentElement?.querySelector<HTMLElement>(".workspace");
    if (background) background.inert = true;
    const focusable = () => [
      ...panel.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"),
    ];
    focusable()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onNavigate();
      }
      if (event.key === "Tab") {
        const elements = focusable();
        const first = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown, true);
    return () => {
      document.removeEventListener("keydown", keydown, true);
      if (background) background.inert = false;
      if (previous?.isConnected) previous.focus();
    };
  }, [mobile, onNavigate]);
  return (
    <aside
      ref={sidebar}
      className={mobile ? "sidebar open" : "sidebar"}
      role={mobile ? "dialog" : undefined}
      aria-modal={mobile ? true : undefined}
      aria-label={mobile ? "Workspace navigation" : undefined}
    >
      {mobile ? (
        <button
          className="mobile-nav-close"
          aria-label="Close navigation"
          onClick={onNavigate}
        >
          <X size={18} />
          Close
        </button>
      ) : null}
      <Link className="wordmark" href={homeFor(user)} onClick={onNavigate}>
        <BookOpen size={27} />
        <span>
          SHIKSHAM<small>APAAR · SYNTHETIC LEDGER</small>
        </span>
      </Link>
      <div className="sidebar-section">WORKSPACE</div>
      <nav aria-label="Workspace navigation">
        {user.role === "STUDENT" ? (
          <Link
            className={path.startsWith("/students/") ? "active" : ""}
            href={homeFor(user)}
            onClick={onNavigate}
          >
            <BookOpen size={18} />
            My Passport
          </Link>
        ) : null}
        {user.role === "STUDENT" ? (
          <Link href={homeFor(user) + "/timeline"} onClick={onNavigate}>
            <BookOpen size={18} />
            My Timeline
          </Link>
        ) : null}
        {NAVIGATION.filter((n) =>
          (n[3] as readonly string[]).includes(user.role),
        ).map(([href, label, Icon]) => (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={
              path === href ||
              (href !== "/students" && path.startsWith(href + "/"))
                ? "active"
                : ""
            }
            aria-current={path === href ? "page" : undefined}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <span className="synthetic-seal">S</span>
        <div>
          SYNTHETIC DATA ONLY<p>No official verification</p>
        </div>
      </div>
    </aside>
  );
}

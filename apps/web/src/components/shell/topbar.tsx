"use client";

import { LogOut, Menu } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { homeFor, signOut } from "@/lib/auth";
import type { User, Envelope, Row } from "@/lib/schemas";
import { useData } from "@/hooks/use-data";
import { text } from "@/lib/format";
import { Breadcrumb } from "./breadcrumb";
import { GlobalSearch } from "./global-search";

export function Topbar({
  user,
  path,
  mobile,
  onToggle,
}: {
  user: User;
  path: string;
  mobile: boolean;
  onToggle: () => void;
}) {
  const router = useRouter();
  const client = useQueryClient();
  const [leaving, setLeaving] = useState(false);
  const params = useSearchParams();
  const institutions = useData<Envelope>(
    user.role === "STUDENT" ? null : "/institutions",
  );
  const passport = useData<Row>(
    user.role === "STUDENT" && user.student_id
      ? "/students/" + user.student_id
      : null,
  );
  const institutionName =
    user.role === "STUDENT"
      ? (passport.data?.profile as Row | undefined)?.institution_name
      : institutions.data?.items.find((row) => row.id === user.institution_id)
          ?.name;
  return (
    <header className="topbar">
      <button
        className="mobile-toggle"
        aria-label="Toggle navigation"
        aria-expanded={mobile}
        onClick={onToggle}
      >
        <Menu />
      </button>
      <Breadcrumb path={path} home={homeFor(user)} />
      <div className="user-menu">
        <GlobalSearch user={user} />
        {user.role === "ADMIN" ? (
          <select
            aria-label="Aggregate institution"
            className="scope-switcher"
            value={params.get("institution_id") || ""}
            onChange={(event) =>
              router.push(
                event.target.value
                  ? "/oversight?institution_id=" +
                      encodeURIComponent(event.target.value)
                  : "/oversight",
              )
            }
          >
            <option value="">All institutions</option>
            {institutions.data?.items.map((row) => (
              <option key={text(row.id)} value={text(row.id)}>
                {text(row.name)}
              </option>
            ))}
          </select>
        ) : null}
        <span>
          {user.full_name}
          <small>{user.role.replaceAll("_", " ")}</small>
          <small className="institution-context">
            {institutionName
              ? text(institutionName)
              : user.role === "OFFICER"
                ? `${user.assigned_institutions.length} assigned institutions`
                : user.role === "ADMIN"
                  ? "Aggregate access"
                  : "Institution scope"}
          </small>
        </span>
        <button
          aria-label="Sign out"
          disabled={leaving}
          onClick={async () => {
            setLeaving(true);
            try {
              await signOut();
            } finally {
              client.clear();
              router.replace("/login");
            }
          }}
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}

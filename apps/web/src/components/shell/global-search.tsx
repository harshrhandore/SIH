"use client";

import Link from "next/link";
import { Search, X, ArrowUpRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { NAVIGATION } from "@/lib/constants";
import { homeFor } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";
import type { User } from "@/lib/schemas";
import type { components } from "@/lib/generated/api";

export function GlobalSearch({ user }: { user: User }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const canSearch = user.role === "OPERATOR" || user.role === "OFFICER";
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (document.querySelector('.sidebar[aria-modal="true"]')) return;
        setOpen(true);
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    if (open && dialog.current && !dialog.current.open) {
      dialog.current.showModal();
      dialog.current.querySelector<HTMLInputElement>("input")?.focus();
    }
  }, [open]);
  const results = useQuery<components["schemas"]["SearchResponse"], ApiError>({
    queryKey: queryKeys.studentSearch(user, debounced),
    queryFn: ({ signal }) =>
      api("/students/search?q=" + encodeURIComponent(debounced), { signal }),
    enabled:
      open && canSearch && debounced.length >= 2 && query.trim() === debounced,
  });
  const links: { href: string; label: string }[] = NAVIGATION.filter((n) =>
    (n[3] as readonly string[]).includes(user.role),
  ).map(([href, label]) => ({ href, label: String(label) }));
  if (user.role === "STUDENT")
    links.unshift({ href: homeFor(user), label: "My Passport" });
  if (user.role === "STUDENT")
    links.push({ href: homeFor(user) + "/timeline", label: "My Timeline" });
  const matchingLinks = links.filter((n) =>
    n.label.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const close = () => dialog.current?.close();
  const showStudents =
    canSearch && debounced.length >= 2 && query.trim() === debounced;
  return (
    <>
      <button
        type="button"
        aria-label="Search workspace (Ctrl+K)"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <Search size={18} />
      </button>
      <dialog
        ref={dialog}
        className="command-palette"
        aria-labelledby="workspace-search-title"
        onClose={() => {
          setOpen(false);
          setQuery("");
        }}
        onKeyDown={(event) => {
          if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
          const targets = Array.from(
            dialog.current?.querySelectorAll<HTMLElement>(
              "input, .palette-results a",
            ) || [],
          );
          const index = targets.indexOf(document.activeElement as HTMLElement);
          if (!targets.length) return;
          event.preventDefault();
          targets[
            (index + (event.key === "ArrowDown" ? 1 : -1) + targets.length) %
              targets.length
          ].focus();
        }}
      >
        <div className="palette-heading">
          <h2 id="workspace-search-title">Search workspace</h2>
          <button type="button" aria-label="Close search" onClick={close}>
            <X size={18} />
          </button>
        </div>
        <label className="sr-only" htmlFor="workspace-search-query">
          Find a page or student
        </label>
        <input
          id="workspace-search-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={100}
          placeholder={
            canSearch ? "Find a page or student…" : "Find an available page…"
          }
          autoComplete="off"
        />
        <div className="palette-results">
          {matchingLinks.length ? (
            <>
              <div className="eyebrow">Pages</div>
              {matchingLinks.map((n) => (
                <Link key={n.href} href={n.href} onClick={close}>
                  {n.label}
                  <ArrowUpRight size={16} />
                </Link>
              ))}
            </>
          ) : null}
          {showStudents ? (
            <div aria-live="polite">
              <div className="eyebrow">Students in your scope</div>
              {results.isFetching ? (
                <p role="status">Searching records…</p>
              ) : null}
              {results.error ? (
                <div role="alert">
                  <p>{results.error.message}</p>
                  <small>{results.error.requestId}</small>
                  <button onClick={() => results.refetch()}>
                    Retry search
                  </button>
                </div>
              ) : (
                results.data?.items.map((student) => (
                  <Link
                    key={student.id}
                    href={"/students/" + student.id}
                    onClick={close}
                  >
                    <span>
                      {student.full_name || "Unnamed record"}
                      <small>
                        {student.apaar_id || "Synthetic ID pending"}
                      </small>
                    </span>
                    <ArrowUpRight size={16} />
                  </Link>
                ))
              )}
              {!results.isFetching &&
              !results.error &&
              results.data?.total === 0 ? (
                <p>No matching students in your authorized scope.</p>
              ) : null}
            </div>
          ) : null}
          {!matchingLinks.length && !showStudents ? (
            <p>
              {canSearch
                ? "Enter at least two characters to search student records."
                : "No available pages match your search."}
            </p>
          ) : null}
        </div>
        <p className="palette-hint">↑ ↓ Move · Enter Open · Esc Close</p>
      </dialog>
    </>
  );
}

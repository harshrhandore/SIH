"use client";
import { useState } from "react";
import { Title } from "@/components/shared/page-heading";

export function Architecture() {
  const [tab, setTab] = useState("Search");
  return (
    <>
      <Title
        eyebrow="ONE LOGIN · ONE DATABASE"
        title="System architecture"
        description="A modular monolith with clear privacy, evidence and mock boundaries."
      />
      <div className="section-nav">
        {["Search", "Import", "Core ER", "Governance ER", "AI ER"].map((t) => (
          <button
            className={tab === t ? "selected" : ""}
            key={t}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <section className="panel padded architecture">
        <div className="diagram-node">Browser · synthetic role accounts</div>
        <div className="connector">↓ same-origin HttpOnly cookies</div>
        <div className="diagram-node">
          Next.js App Router + scoped backend proxy
        </div>
        <div className="connector">↓ authorization · CSRF · validation</div>
        <div className="diagram-grid">
          {[
            "Authentication & scope",
            "Import & staging",
            "Human review",
            "Indexed search & cache",
            "Audit append & verifier",
            "Passport & intelligence",
          ].map((n) => (
            <div
              className={
                "diagram-node " +
                ((tab === "Search" && n.includes("search")) ||
                (tab === "Import" && n.includes("Import"))
                  ? "highlight"
                  : "")
              }
              key={n}
            >
              {n}
            </div>
          ))}
        </div>
        <div className="connector">↓ transactions · scoped SQL</div>
        <div className="diagram-node database">
          PostgreSQL 16
          <br />
          <small>
            Relational tables · B-tree / GIN · Materialized views · Immutable
            audit
          </small>
        </div>
        <div className="diagram-grid">
          <div className="diagram-node">
            Persistent local storage
            <br />
            <small>PDF text / OCR fallback</small>
          </div>
          <div className="diagram-node dashed">
            MockApaarAdapter
            <br />
            <small>MOCK · not official</small>
          </div>
          <div className="diagram-node dashed">
            Optional Gemini boundary
            <br />
            <small>Disabled · deterministic fallback</small>
          </div>
        </div>
        <p className="note">
          {tab === "Search"
            ? "Search: scope → epoch → scoped cache → exact count + indexed page → measured response."
            : tab === "Import"
              ? "Import: file guard → staging → mapping → 250-row atomic checkpoints → version + findings + case + audit → live counts."
              : tab === "Core ER"
                ? "Institutions 1:N Programs / Students. Students 1:N Enrolments / Performance. Programs 1:1 Expected counts."
                : tab === "Governance ER"
                  ? "Students 1:N Cases / Versions. Cases 1:N Decisions. Chains 1:N immutable Events. Users N:M Institutions."
                  : "Students 1:N Certificates / Career sessions. Certificates 1:N Verifications. Skills N:M Students. Students 1:1 Trust score."}
        </p>
      </section>
    </>
  );
}

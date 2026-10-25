"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import {
  BookOpen,
  LayoutDashboard,
  Upload,
  Search,
  ClipboardCheck,
  ChartNoAxesCombined,
  Layers,
  LogOut,
  Menu,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  AlertTriangle,
  ShieldCheck,
  FileText,
  ArrowRight,
  RefreshCw,
  Printer,
  ChevronRight,
  Settings,
  GraduationCap,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";

type Row = Record<string, unknown>;
type User = {
  id: string;
  full_name: string;
  role: string;
  institution_id: string | null;
  student_id: string | null;
  assigned_institutions: string[];
};
type Envelope = { items: Row[]; total: number; [key: string]: unknown };
const text = (v: unknown) =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);
const number = (v: unknown) => Number(v || 0).toLocaleString("en-IN");

function useData<T>(path: string | null, interval = 0, grant = "") {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState<ApiError | null>(null),
    [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!path) {
      setLoading(false);
      return;
    }
    try {
      const result = await api<T>(path, {
        headers: grant ? { "X-Case-Access": grant } : {},
      });
      setData(result);
      setError(null);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoading(false);
    }
  }, [path, grant]);
  useEffect(() => {
    let active = true;
    async function fetchData() {
      if (!path) {
        setLoading(false);
        return;
      }
      try {
        const result = await api<T>(path, {
          headers: grant ? { "X-Case-Access": grant } : {},
        });
        if (active) {
          setData(result);
          setError(null);
        }
      } catch (e) {
        if (active) setError(e as ApiError);
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchData();
    const id = interval
      ? setInterval(() => {
          if (!document.hidden) fetchData();
        }, interval)
      : undefined;
    return () => {
      active = false;
      if (id) clearInterval(id);
    };
  }, [path, interval, grant]);
  return { data, error, loading, reload };
}
function State({
  loading,
  error,
  children,
  retry,
}: {
  loading?: boolean;
  error?: ApiError | null;
  children: React.ReactNode;
  retry?: () => void;
}) {
  if (error)
    return (
      <div className="error" role="alert">
        <AlertTriangle />
        {error.message}
        <small>{error.requestId}</small>
        <button onClick={retry}>Retry</button>
      </div>
    );
  if (loading)
    return (
      <div role="status" aria-label="Loading records" className="skeleton">
        <span />
        <span />
        <span />
      </div>
    );
  return children;
}
function Badge({ value }: { value: unknown }) {
  const v = text(value);
  const ok =
    v.includes("PASSED") ||
    v === "APPROVED" ||
    v === "VERIFIED_LOCAL" ||
    v === "COMPLETED";
  const pending = v.includes("PENDING");
  return (
    <span
      className={
        "badge " +
        (ok
          ? "ok"
          : pending
            ? "pending"
            : v === "INCOMPLETE"
              ? "neutral"
              : "warn")
      }
    >
      {ok ? (
        <CheckCircle2 size={13} />
      ) : pending ? (
        <Clock3 size={13} />
      ) : (
        <AlertTriangle size={13} />
      )}{" "}
      {v.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}
function Title({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {description ? <p className="muted">{description}</p> : null}
      </div>
      <div className="heading-actions">{children}</div>
    </header>
  );
}
function Table({
  rows,
  columns,
  href,
}: {
  rows: Row[];
  columns: [string, string][];
  href?: (row: Row) => string;
}) {
  if (!rows.length)
    return (
      <div className="empty">
        <FileText />
        <h3>No records to display</h3>
        <p>Try clearing your filters or complete a synthetic import.</p>
      </div>
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Scrollable record table"
    >
      <table>
        <thead>
          <tr>
            {columns.map(([key, label]) => (
              <th key={key}>{label}</th>
            ))}
            {href ? (
              <th>
                <span className="sr-only">Open record</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={text(r.id || r.case_id || i)}>
              {columns.map(([key]) => (
                <td key={key}>
                  {key.includes("status") ? (
                    <Badge value={r[key]} />
                  ) : key === "full_name" && href ? (
                    <Link className="record-link" href={href(r)}>
                      {text(r[key])}
                    </Link>
                  ) : (
                    text(r[key])
                  )}
                </td>
              ))}
              {href ? (
                <td>
                  <Link
                    aria-label={
                      "Open " +
                      text(r.full_name || r.filename || r.id || r.case_id)
                    }
                    href={href(r)}
                  >
                    <ArrowUpRight size={17} />
                  </Link>
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const nav = [
  [
    "/dashboard",
    "Institution ledger",
    LayoutDashboard,
    ["OPERATOR", "OFFICER"],
  ],
  ["/imports", "Imports", Upload, ["OPERATOR", "OFFICER"]],
  ["/students", "Student search", Search, ["OPERATOR", "OFFICER"]],
  [
    "/cases",
    "Verification cases",
    ClipboardCheck,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
  ["/oversight", "Institution oversight", Layers, ["ADMIN"]],
  [
    "/analytics",
    "Analytics",
    ChartNoAxesCombined,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
  ["/certificates", "Certificates", FileText, ["STUDENT"]],
  ["/career", "Career Copilot", GraduationCap, ["STUDENT"]],
  [
    "/architecture",
    "Architecture",
    Layers,
    ["OPERATOR", "OFFICER", "ADMIN", "STUDENT"],
  ],
  [
    "/settings/demo",
    "Demo controls",
    Settings,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
] as const;

export default function Workspace() {
  const path = usePathname();
  const session = useData<User>("/auth/me");
  const [mobile, setMobile] = useState(false);
  const user = session.data;
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        location.href = "/students";
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
  if (!user)
    return (
      <main className="boot">
        <State
          loading={session.loading}
          error={session.error}
          retry={session.reload}
        >
          <Link href="/login">Sign in to open the ledger</Link>
        </State>
      </main>
    );
  let content: React.ReactNode;
  if (path === "/dashboard") content = <Dashboard user={user} />;
  else if (path === "/students") content = <SearchScreen />;
  else if (path.startsWith("/students/"))
    content = (
      <PassportScreen
        id={path.split("/")[2]}
        print={path.endsWith("/print")}
        timeline={path.endsWith("/timeline")}
      />
    );
  else if (path === "/imports/new") content = <ImportWizard user={user} />;
  else if (path === "/imports") content = <ImportList />;
  else if (path.startsWith("/imports/"))
    content = <ImportDetail id={path.split("/")[2]} />;
  else if (path === "/cases") content = <Cases />;
  else if (path.startsWith("/cases/"))
    content = <CaseDetail id={path.split("/")[2]} user={user} />;
  else if (path === "/certificates")
    content = <CertificateUpload user={user} />;
  else if (path.startsWith("/certificates/") || path.startsWith("/fraud/"))
    content = <CertificateReport id={path.split("/")[2]} />;
  else if (path === "/career") content = <CareerScreen user={user} />;
  else if (path === "/analytics") content = <Analytics user={user} />;
  else if (path === "/oversight") content = <Oversight />;
  else if (path === "/architecture") content = <Architecture />;
  else content = <DemoControls user={user} />;
  return (
    <div className="app-shell">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <Link
          className="wordmark"
          href={
            user.role === "STUDENT"
              ? "/students/" + user.student_id
              : "/dashboard"
          }
        >
          <BookOpen size={27} />
          <span>
            SHIKSHAM<small>APAAR · SYNTHETIC LEDGER</small>
          </span>
        </Link>
        <div className="sidebar-section">WORKSPACE</div>
        <nav>
          {user.role === "STUDENT" ? (
            <Link
              className={path.startsWith("/students/") ? "active" : ""}
              href={"/students/" + user.student_id}
            >
              <BookOpen size={18} />
              My Passport
            </Link>
          ) : null}
          {nav
            .filter((n) => (n[3] as readonly string[]).includes(user.role))
            .map(([href, label, Icon]) => (
              <Link
                onClick={() => setMobile(false)}
                className={
                  path === href ||
                  (href !== "/students" && path.startsWith(href + "/"))
                    ? "active"
                    : ""
                }
                key={href}
                href={href}
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
      <div className="workspace">
        <header className="topbar">
          <button
            className="mobile-toggle"
            aria-label="Toggle navigation"
            aria-expanded={mobile}
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <span className="breadcrumb">
            Workspace <ChevronRight size={13} />
            {path.split("/")[1].replaceAll("-", " ")}
          </span>
          <div className="user-menu">
            <span>
              {user.full_name}
              <small>{user.role.replaceAll("_", " ")}</small>
            </span>
            <button
              aria-label="Sign out"
              onClick={async () => {
                try {
                  await api("/auth/logout", { method: "POST", body: "{}" });
                } finally {
                  location.href = "/login";
                }
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <div className="scope-strip">
          <ShieldCheck size={14} /> Synthetic demonstration{" "}
          <span>
            Local checks and mock results are distinct from official
            verification.
          </span>
        </div>
        <main className="content">{content}</main>
        <footer className="footer">
          SHIKSHAM APAAR{" "}
          <span>Evidence you can inspect. Decisions you can trace.</span>
          <span>SYNTHETIC PROTOTYPE</span>
        </footer>
      </div>
    </div>
  );
}

function Dashboard({ user }: { user: User }) {
  const url =
    "/dashboard" +
    (user.role === "OFFICER"
      ? "?institution_id=" + user.assigned_institutions[0]
      : "");
  const query = useData<Row>(url, 5000);
  const d = query.data;
  return (
    <>
      <Title
        eyebrow="RECORDS & ACCOUNTABILITY"
        title="Institution ledger"
        description={
          d
            ? text(d.institution_name)
            : "Your institution’s live record quality and review activity."
        }
      >
        <Link className="primary" href="/imports/new">
          <Upload size={17} /> Import records
        </Link>
      </Title>
      <State {...query} retry={query.reload}>
        {d ? (
          <>
            <div className="metrics">
              {[
                ["total", "Total records", "All submitted student records"],
                ["clean", "Passed local checks", "Ready for the next step"],
                ["flagged", "Flagged for review", "Human attention required"],
                ["incomplete", "Incomplete", "Mandatory information missing"],
              ].map(([key, label, detail], i) => (
                <Link
                  href={"/students?quality=" + key}
                  className={"metric metric-" + i}
                  key={key}
                >
                  <div className="metric-label">
                    {label}
                    <ArrowUpRight size={16} />
                  </div>
                  <strong>{number(d[key])}</strong>
                  <small>{detail}</small>
                </Link>
              ))}
            </div>
            <div className="two-columns">
              <section className="panel submission">
                <div className="panel-heading">
                  <h2>Submission coverage</h2>
                  <span className="mono">{text(d.submission_percent)}%</span>
                </div>
                <div className="progress">
                  <div style={{ width: text(d.submission_percent) + "%" }} />
                </div>
                <div className="spread">
                  <p>
                    <b>{number(d.total)}</b> submitted
                  </p>
                  <p>
                    <b>{number(d.missing_records)}</b> missing records
                  </p>
                </div>
                <p className="note">
                  Measured against this institution’s expected record count.
                </p>
              </section>
              <section className="panel review-card">
                <div className="eyebrow">THE REVIEW DESK</div>
                <h2>{number(d.pending_reviews)} records need attention</h2>
                <p className="muted">
                  {number(d.pending_corrections)} pending operator corrections.
                  Every correction retains its source and history.
                </p>
                <Link href="/cases">
                  Open review queue <ArrowRight size={16} />
                </Link>
              </section>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">IMPORT REGISTER</div>
                  <h2>Recent submissions</h2>
                </div>
                <Link href="/imports">
                  View all <ArrowRight size={15} />
                </Link>
              </div>
              <Table
                rows={d.recent_imports as Row[]}
                columns={[
                  ["filename", "Source file"],
                  ["total_rows", "Records"],
                  ["clean_rows", "Passed"],
                  ["flagged_rows", "Flagged"],
                  ["status", "Status"],
                ]}
                href={(r) => "/imports/" + r.id}
              />
            </section>
            <p className="note">
              Live counters · refresh every 5 seconds · source epoch{" "}
              {text(d.data_epoch)}
            </p>
          </>
        ) : null}
      </State>
    </>
  );
}

function SearchScreen() {
  const [input, setInput] = useState(""),
    [q, setQ] = useState(""),
    [branch, setBranch] = useState(""),
    [year, setYear] = useState(""),
    [page, setPage] = useState(1);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(input);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [input]);
  const query = useData<Envelope>(
    "/students/search?" +
      new URLSearchParams({
        q,
        branch,
        ...(year ? { current_year: year } : {}),
        page: String(page),
      }).toString(),
  );
  return (
    <>
      <Title
        eyebrow="THE STUDENT REGISTER"
        title="Student search"
        description="Search within your authorized institutions. Every count comes from the ledger."
      />
      <section className="panel">
        <div className="filters">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Search student records"
              placeholder="Name, synthetic ID or enrollment number"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          <label>
            Branch
            <select
              value={branch}
              onChange={(e) => {
                setBranch(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All branches</option>
              {["CSE", "ECE", "ME", "IT", "AI&DS", "GENERAL"].map((b) => (
                <option key={b}>{b}</option>
              ))}
            </select>
          </label>
          <label>
            Year
            <select value={year} onChange={(e) => setYear(e.target.value)}>
              <option value="">All years</option>
              {[1, 2, 3, 4].map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </label>
          <button
            onClick={() => {
              setInput("");
              setBranch("");
              setYear("");
            }}
          >
            Clear
          </button>
        </div>
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <div className="search-summary">
                Found <b>{number(query.data.total)}</b>{" "}
                {query.data.total === 1 ? "record" : "records"} in{" "}
                <span className="mono">{text(query.data.took_ms)} ms</span>
                <span className="cache">{text(query.data.cache)}</span>
                <small>API time</small>
              </div>
              <Table
                rows={query.data.items}
                columns={[
                  ["full_name", "Student name"],
                  ["apaar_id", "Synthetic identifier"],
                  ["program", "Program"],
                  ["current_year", "Year"],
                  ["data_quality_status", "Local status"],
                ]}
                href={(r) => "/students/" + r.id}
              />
              <div className="pagination">
                <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                  Previous
                </button>
                <span>
                  Page {page} · {number(query.data.total)} records
                </span>
                <button
                  disabled={page * 25 >= query.data.total}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}

function ImportList() {
  const query = useData<Envelope>("/imports");
  return (
    <>
      <Title
        eyebrow="SOURCE REGISTER"
        title="Imports"
        description="Synthetic submissions and their validation history."
      >
        <Link className="primary" href="/imports/new">
          <Upload size={17} /> Import records
        </Link>
      </Title>
      <section className="panel">
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["filename", "Source file"],
              ["total_rows", "Records"],
              ["clean_rows", "Passed"],
              ["flagged_rows", "Flagged"],
              ["status", "Status"],
            ]}
            href={(r) => "/imports/" + r.id}
          />
        </State>
      </section>
    </>
  );
}

const fields = [
  "submitted_apaar_id",
  "submitted_enrollment_no",
  "full_name",
  "dob",
  "parent_name",
  "program_code",
  "admission_year",
  "current_year",
  "term_no",
  "sgpa",
  "credits",
  "email",
  "gender",
];
function ImportWizard({ user }: { user: User }) {
  const [file, setFile] = useState<File | null>(null),
    [confirmed, setConfirmed] = useState(false),
    [batch, setBatch] = useState<Row | null>(null),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [preview, setPreview] = useState<Row[] | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function upload() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("institution_id", user.institution_id || "");
      const result = await api<Row>("/imports", { method: "POST", body: form });
      setBatch(result);
      const suggested = result.suggested_mapping as Record<
        string,
        { column: string }
      >;
      setMapping(
        Object.fromEntries(
          Object.entries(suggested).map(([k, v]) => [k, v.column]),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function map() {
    setBusy(true);
    setError("");
    try {
      const result = await api<Row>(
        "/imports/" + batch?.batch_id + "/mapping",
        {
          method: "PUT",
          body: JSON.stringify({
            mapping: Object.fromEntries(
              Object.entries(mapping).filter(([, v]) => v),
            ),
            date_format: "DD/MM/YYYY",
          }),
        },
      );
      setPreview(result.preview as Row[]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function validate() {
    setBusy(true);
    try {
      await api("/imports/" + batch?.batch_id + "/validate", {
        method: "POST",
        body: JSON.stringify({ confirm_synthetic_data: confirmed }),
      });
      location.href = "/imports/" + batch?.batch_id;
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="NEW SUBMISSION"
        title="Import synthetic records"
        description="Keep the source. Check every row. Resolve discrepancies with a person."
      />
      <ol className="steps">
        {["Upload", "Map", "Preview", "Validate", "Report"].map((s, i) => (
          <li
            className={(preview ? 2 : batch ? 1 : 0) === i ? "current" : ""}
            key={s}
          >
            <span>{i + 1}</span>
            {s}
          </li>
        ))}
      </ol>
      <section className="panel padded">
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
        {!batch ? (
          <>
            <h2>Choose a source file</h2>
            <p>CSV or XLSX · up to 1,000 rows · 20 MiB maximum</p>
            <a href="/api/backend/demo/fixtures/import_csv" download>
              Download the 1,000-row synthetic fixture
            </a>
            <label className="dropzone">
              <Upload size={32} />
              <span>{file?.name || "Choose a CSV or XLSX file"}</span>
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />{" "}
              I confirm this dataset is synthetic.
            </label>
            <button
              className="primary"
              disabled={!file || !confirmed || busy}
              onClick={upload}
            >
              {busy ? "Saving source…" : "Continue to mapping"}
              <ArrowRight size={16} />
            </button>
          </>
        ) : !preview ? (
          <>
            <h2>Map source columns</h2>
            <p className="muted">
              Mandatory fields: enrollment, name, DOB, program, admission year
              and current year. Dates use DD/MM/YYYY.
            </p>
            <div className="mapping-grid">
              {fields.map((field) => (
                <label key={field}>
                  {field.replaceAll("_", " ")}
                  <select
                    value={mapping[field] || ""}
                    onChange={(e) =>
                      setMapping({ ...mapping, [field]: e.target.value })
                    }
                  >
                    <option value="">Ignore optional column</option>
                    {(batch.headers as string[]).map((h) => (
                      <option key={h}>{h}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <button className="primary" disabled={busy} onClick={map}>
              {busy ? "Checking mapping…" : "Preview 20 rows"}
            </button>
          </>
        ) : (
          <>
            <h2>Preview the first 20 rows</h2>
            <p className="note">
              Preview is not full-file validation. Missing identifiers remain
              visible in the source.
            </p>
            <Table
              rows={preview.map((p) => ({
                row_no: p.row_no,
                ...(p.normalized as Row),
              }))}
              columns={[
                ["row_no", "Row"],
                ["full_name", "Name"],
                ["submitted_apaar_id", "Submitted ID"],
                ["dob", "DOB"],
                ["program_code", "Program"],
              ]}
            />
            <button className="primary" disabled={busy} onClick={validate}>
              {busy
                ? "Starting validation…"
                : "Validate " + number(batch.total_rows) + " records"}
            </button>
          </>
        )}
      </section>
    </>
  );
}

function ImportDetail({ id }: { id: string }) {
  const query = useData<Row>("/imports/" + id, 1000);
  const d = query.data;
  const report = d?.report as Row | undefined;
  const job = d?.job as Row | undefined;
  return (
    <>
      <Title
        eyebrow="VALIDATION REPORT"
        title={d ? text(d.filename) : "Import report"}
        description="Checkpointed validation with original source rows retained."
      />
      <State {...query} retry={query.reload}>
        {d && report ? (
          <>
            <section className="panel padded">
              <Badge value={d.status} />
              <div className="spread">
                <h2>
                  {number(report.processed_rows)} / {number(report.total_rows)}{" "}
                  records processed
                </h2>
                <span className="mono">{text(job?.progress || 0)}%</span>
              </div>
              <div className="progress">
                <div style={{ width: text(job?.progress || 0) + "%" }} />
              </div>
              {d.status === "FAILED" ? (
                <div className="error">
                  {text(job?.error_message)}
                  <button
                    onClick={async () => {
                      await api("/import-jobs/" + job?.id + "/retry", {
                        method: "POST",
                        body: JSON.stringify({
                          reason:
                            "Retry the interrupted synthetic import from its checkpoint.",
                        }),
                      });
                      query.reload();
                    }}
                  >
                    Retry saved checkpoint
                  </button>
                </div>
              ) : null}
            </section>
            <div className="metrics">
              {[
                ["clean", "Passed local checks"],
                ["flagged", "Flagged for review"],
                ["incomplete", "Incomplete"],
                ["affected_rows", "Need attention"],
              ].map(([key, label]) => (
                <div className="metric" key={key}>
                  <span>{label}</span>
                  <strong>{number(report[key])}</strong>
                </div>
              ))}
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>Primary findings</h2>
                <a href={"/api/backend/imports/" + id + "/errors.csv"} download>
                  Download error CSV
                </a>
              </div>
              <Table
                rows={report.primary_findings as Row[]}
                columns={[
                  ["code", "Rule"],
                  ["count", "Affected rows"],
                ]}
              />
              <div className="padded">
                <p>
                  {number(report.secondary_findings)} secondary findings ·{" "}
                  {number(report.all_findings)} findings in total
                </p>
                <Link className="primary" href="/cases">
                  Open cases <ArrowRight size={16} />
                </Link>{" "}
                <Link className="button" href="/dashboard">
                  View institution ledger
                </Link>
              </div>
            </section>
          </>
        ) : null}
      </State>
    </>
  );
}

function Cases() {
  const [status, setStatus] = useState("OPEN"),
    [q, setQ] = useState("");
  const query = useData<Envelope>(
    "/cases?" + new URLSearchParams({ status, q }).toString(),
  );
  return (
    <>
      <Title
        eyebrow="HUMAN REVIEW"
        title="Verification cases"
        description="Inspect the evidence. Record the reason. Keep every decision traceable."
      />
      <section className="panel">
        <div className="filters">
          <label>
            Case status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {[
                "OPEN",
                "CORRECTION_REQUESTED",
                "ESCALATED",
                "APPROVED",
                "",
              ].map((v) => (
                <option key={v} value={v}>
                  {v || "All statuses"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Enrollment or name
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="DEMO-A-0032"
            />
          </label>
        </div>
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["full_name", "Student"],
              ["masked_name", "Masked name"],
              ["submitted_enrollment_no", "Enrollment"],
              ["opened_reason", "Primary rule"],
              ["status", "Status"],
            ]}
            href={(r) => "/cases/" + (r.id || r.case_id)}
          />
        </State>
      </section>
    </>
  );
}

function CaseDetail({ id, user }: { id: string; user: User }) {
  const [grant, setGrant] = useState("");
  const query = useData<Row>("/cases/" + id, 0, grant);
  const [note, setNote] = useState(""),
    [correction, setCorrection] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const data = query.data,
    caseRow = data?.case as Row | undefined,
    passport = data?.student as Row | undefined,
    profile = passport?.profile as Row | undefined;
  async function decide(action: string) {
    setBusy(true);
    setMessage("");
    try {
      await api("/cases/" + id + "/decisions", {
        method: "POST",
        headers: grant ? { "X-Case-Access": grant } : {},
        body: JSON.stringify({
          expected_version: caseRow?.version_no,
          action,
          reason: note,
          requested_fields:
            action === "REQUEST_CORRECTION" ? ["submitted_apaar_id"] : [],
        }),
      });
      setMessage("Decision recorded.");
      query.reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function correct() {
    setBusy(true);
    try {
      await api("/students/" + caseRow?.student_id, {
        method: "PATCH",
        body: JSON.stringify({
          expected_version: profile?.version_no,
          patch: { submitted_apaar_id: correction },
          reason: note,
        }),
      });
      setMessage("Correction saved. Officer review is required.");
      query.reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="CASE FILE"
        title={profile ? text(profile.full_name) : "Verification case"}
        description={"Case " + id}
      />
      <State {...query} retry={query.reload}>
        {data && caseRow ? (
          <>
            <section className="panel padded">
              <Badge value={caseRow.status} />
              <h2>{text(caseRow.opened_reason).replaceAll("_", " ")}</h2>
              {data.masked ? (
                <div>
                  <p>
                    This case is masked. An administrator can inspect raw
                    details only with a reasoned, case-bound escalation grant.
                  </p>
                  {caseRow.status === "ESCALATED" ? (
                    <>
                      <label>
                        Reason for inspecting this escalated case
                        <textarea
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          maxLength={1000}
                        />
                      </label>
                      <button
                        disabled={note.trim().length < 10 || busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            const r = await api<{ access_grant: string }>(
                              "/cases/" + id + "/access",
                              {
                                method: "POST",
                                body: JSON.stringify({ reason: note }),
                              },
                            );
                            setGrant(r.access_grant);
                            setTimeout(() => {
                              setGrant("");
                              query.reload();
                            }, 300000);
                          } catch (e) {
                            setMessage((e as Error).message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Record reason and inspect case
                      </button>
                    </>
                  ) : null}
                </div>
              ) : (
                <>
                  <p className="mono">
                    {text(profile?.apaar_id)} · Version{" "}
                    {text(profile?.version_no)}
                  </p>
                  <div className="two-columns">
                    <div>
                      <h3>Current findings</h3>
                      {(data.findings as Row[]).length ? (
                        (data.findings as Row[]).map((f) => (
                          <div className="finding" key={text(f.code)}>
                            <Badge value={f.severity} />
                            <h3>{text(f.code).replaceAll("_", " ")}</h3>
                            <p>{text(f.explanation)}</p>
                          </div>
                        ))
                      ) : (
                        <p>
                          <CheckCircle2 size={17} /> No unresolved findings.
                        </p>
                      )}
                      <h3>Candidate review</h3>
                      <Table
                        rows={data.duplicates as Row[]}
                        columns={[
                          ["match_type", "Type"],
                          ["score", "Score"],
                          ["status", "Status"],
                        ]}
                      />
                    </div>
                    <div className="review-form">
                      <h3>Record the next action</h3>
                      <label>
                        Reason (10–1,000 characters)
                        <textarea
                          minLength={10}
                          maxLength={1000}
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          placeholder="Describe the source evidence and your decision."
                        />
                      </label>
                      {user.role === "OPERATOR" ? (
                        <>
                          <label>
                            Corrected synthetic ID
                            <input
                              value={correction}
                              onChange={(e) => setCorrection(e.target.value)}
                              placeholder="Value from fixtures/manifest.json"
                            />
                          </label>
                          <button
                            className="primary"
                            disabled={
                              note.trim().length < 10 || busy || !correction
                            }
                            onClick={correct}
                          >
                            {busy ? "Saving…" : "Save correction"}
                          </button>
                        </>
                      ) : (
                        (data.allowed_actions as string[]).map((action) => (
                          <button
                            className={action === "APPROVE" ? "primary" : ""}
                            disabled={note.trim().length < 10 || busy}
                            key={action}
                            onClick={() => decide(action)}
                          >
                            {action.replaceAll("_", " ")}
                          </button>
                        ))
                      )}
                      <p className="note">
                        Confirmation never merges student identities.
                      </p>
                    </div>
                  </div>
                  <Link href={"/students/" + caseRow.student_id + "/timeline"}>
                    Open audit timeline <ArrowRight size={15} />
                  </Link>
                </>
              )}
              {message ? (
                <p role="status" className="notice">
                  {message}
                </p>
              ) : null}
            </section>
            {data.versions ? (
              <section className="panel">
                <div className="panel-heading">
                  <h2>Immutable version history</h2>
                </div>
                <Table
                  rows={data.versions as Row[]}
                  columns={[
                    ["version_no", "Version"],
                    ["reason", "Reason"],
                    ["created_at", "Created"],
                  ]}
                />
              </section>
            ) : null}
          </>
        ) : null}
      </State>
    </>
  );
}

function PassportScreen({
  id,
  print,
  timeline,
}: {
  id: string;
  print: boolean;
  timeline: boolean;
}) {
  const query = useData<Row>("/students/" + id);
  const data = query.data,
    profile = data?.profile as Row | undefined,
    trust = data?.trust as Row | undefined;
  if (timeline) return <Timeline id={id} />;
  return (
    <>
      <Title
        eyebrow="ACADEMIC PASSPORT"
        title={profile ? text(profile.full_name) : "Academic passport"}
        description="Synthetic academic history · Local consistency, never official verification"
      >
        <Link className="button" href={"/students/" + id + "/print"}>
          <Printer size={16} /> Print passport
        </Link>
        {print ? (
          <button onClick={() => window.print()}>Open print preview</button>
        ) : null}
      </Title>
      <State {...query} retry={query.reload}>
        {data && profile && trust ? (
          <>
            <section className="passport-header panel padded">
              <div className="passport-identity">
                <span className="synthetic-seal large">S</span>
                <div>
                  <div className="eyebrow">
                    {text(profile.institution_name)}
                  </div>
                  <h2>{text(profile.program)}</h2>
                  <p className="mono">{text(profile.apaar_id)}</p>
                  <Badge value={profile.external_status} />
                </div>
              </div>
              <div className="passport-number">
                <span>CGPA</span>
                <strong>{text(data.cgpa)}</strong>
                <small>Credit-weighted · / 10</small>
              </div>
              <div className="trust-ring">
                <strong>{text(trust.score)}</strong>
                <span>Trust / 100</span>
              </div>
            </section>
            <nav className="section-nav">
              <a href="#performance">Performance</a>
              <a href="#evidence">Evidence</a>
              <a href="#trust">Trust formula</a>
              <Link href={"/students/" + id + "/timeline"}>Timeline</Link>
            </nav>
            <section className="panel" id="performance">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">ACADEMIC LEDGER</div>
                  <h2>Performance by term</h2>
                </div>
                <Badge value={profile.data_quality_status} />
              </div>
              <Table
                rows={data.terms as Row[]}
                columns={[
                  ["term_no", "Term"],
                  ["academic_year", "Academic year"],
                  ["credits", "Credits"],
                  ["sgpa", "SGPA"],
                  ["cgpa", "Cumulative CGPA"],
                ]}
              />
            </section>
            <div id="evidence">
              {[
                "certificates",
                "projects",
                "internships",
                "achievements",
                "scholarships",
                "skills",
              ].map((key) => (
                <section className="panel" key={key}>
                  <div className="panel-heading">
                    <h2>{key[0].toUpperCase() + key.slice(1)}</h2>
                    <span className="mono">
                      {(data[key] as Row[]).length} entries
                    </span>
                  </div>
                  <Table
                    rows={data[key] as Row[]}
                    columns={
                      key === "certificates"
                        ? [
                            ["title", "Certificate"],
                            ["issuer", "Issuer"],
                            ["purpose", "Purpose"],
                            ["acceptance_status", "Acceptance"],
                          ]
                        : key === "skills"
                          ? [
                              ["label", "Skill"],
                              ["proficiency", "Proficiency / 5"],
                              ["evidence_kind", "Evidence"],
                            ]
                          : key === "internships"
                            ? [
                                ["organization", "Organization"],
                                ["role", "Role"],
                                ["start_date", "Started"],
                              ]
                            : key === "scholarships"
                              ? [
                                  ["name", "Scholarship"],
                                  ["academic_year", "Year"],
                                  ["amount_inr", "Amount INR"],
                                ]
                              : [
                                  ["title", "Title"],
                                  ["description", "Description"],
                                ]
                    }
                  />
                </section>
              ))}
            </div>
            <section className="panel" id="trust">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">HEURISTIC, NOT VALIDATED</div>
                  <h2>Trust Score · {text(trust.score)} / 100</h2>
                </div>
                <span>Formula version {text(trust.formula_version)}</span>
              </div>
              <Table
                rows={trust.components as Row[]}
                columns={[
                  ["key", "Component"],
                  ["earned", "Earned"],
                  ["max", "Maximum"],
                  ["reason", "Explanation"],
                ]}
              />
              <p className="note padded">
                Mock verification adds zero official points. Trial certificates
                are excluded. Scores are computed from synthetic fixtures
                calibrated for this demonstration.
              </p>
            </section>
          </>
        ) : null}
      </State>
    </>
  );
}

function Timeline({ id }: { id: string }) {
  const query = useData<Envelope>("/students/" + id + "/timeline");
  return (
    <>
      <Title
        eyebrow="ACCOUNTABLE HISTORY"
        title="Audit timeline"
        description="Ticks require verification of the full institution chain containing each event."
      >
        <button onClick={query.reload}>
          <RefreshCw size={16} /> Verify chain
        </button>
      </Title>
      <State {...query} retry={query.reload}>
        {query.data ? (
          <section className="panel padded">
            <p className="notice">
              {query.data.verified
                ? "Full chain verified"
                : "Chain verification failed or unavailable"}{" "}
              · checked head {text(query.data.checked_head_seq)}
            </p>
            <div className="timeline">
              {query.data.items.map((row) => (
                <article key={text(row.event_id)}>
                  <div className="timeline-dot">
                    {row.hash_verified ? (
                      <CheckCircle2 size={17} />
                    ) : (
                      <Clock3 size={17} />
                    )}
                  </div>
                  <div className="eyebrow">
                    {text(row.occurred_at)} · #{text(row.sequence_no)}
                  </div>
                  <h3>{text(row.action).replaceAll("_", " ")}</h3>
                  <p>{text(row.reason)}</p>
                  <p className="muted">{text(row.actor_name)}</p>
                  {Object.keys((row.changes as Row) || {}).length ? (
                    <pre>{JSON.stringify(row.changes, null, 2)}</pre>
                  ) : null}
                  <details>
                    <summary>Stored row hash</summary>
                    <code>{text(row.row_hash)}</code>
                  </details>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </State>
    </>
  );
}

function CertificateUpload({ user }: { user: User }) {
  const [file, setFile] = useState<File | null>(null),
    [purpose, setPurpose] = useState("TRIAL"),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  async function verify() {
    if (!file) return;
    setBusy(true);
    setMessage("Saving file and computing local consistency…");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("purpose", purpose);
      form.set("title", "Synthetic supporting certificate");
      const uploaded = await api<Row>(
        "/students/" + user.student_id + "/certificates",
        { method: "POST", body: form },
      );
      setMessage("Reading text and comparing with the synthetic record…");
      const report = await api<Row>(
        "/certificates/" + uploaded.certificate_id + "/verify",
        { method: "POST", body: "{}" },
      );
      location.href = "/certificates/" + report.verification_id;
    } catch (e) {
      setMessage((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="EXPLAINABLE EVIDENCE"
        title="Certificates"
        description="Check document consistency against your synthetic academic record."
      />
      <section className="panel padded">
        <div className="notice">
          Local consistency checks are not issuer authentication or official
          verification.
        </div>
        <div className="fixture-links">
          <a href="/api/backend/demo/fixtures/genuine_pdf" download>
            Genuine PDF fixture
          </a>
          <a href="/api/backend/demo/fixtures/tampered_pdf" download>
            Tampered PDF fixture
          </a>
          <a href="/api/backend/demo/fixtures/genuine_png" download>
            PNG OCR fixture
          </a>
        </div>
        <label>
          Purpose
          <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
            <option value="TRIAL">
              Trial — excluded from accepted passport and Trust Score
            </option>
            <option value="PASSPORT">
              Passport — requires staff acceptance
            </option>
          </select>
        </label>
        <label className="dropzone">
          <FileText size={32} />
          <span>{file?.name || "Choose PDF, PNG or JPEG"}</span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <p className="note">
          10 MiB maximum · 10 PDF pages · encrypted or active PDFs rejected
        </p>
        <button className="primary" disabled={!file || busy} onClick={verify}>
          {busy ? "Verifying…" : "Verify local consistency"}
          <ShieldCheck size={16} />
        </button>
        <p role="status">{message}</p>
      </section>
    </>
  );
}

function CertificateReport({ id }: { id: string }) {
  const query = useData<Row>("/certificate-verifications/" + id);
  const d = query.data,
    risk = d?.risk as Row | undefined;
  return (
    <>
      <Title
        eyebrow="SYNTHETIC · NOT OFFICIAL VERIFICATION"
        title="Local certificate consistency report"
      />
      <State {...query} retry={query.reload}>
        {d && risk ? (
          <>
            <div className="notice">
              {d.purpose === "TRIAL"
                ? "Verification trial — excluded from accepted passport and Trust Score"
                : "Passport evidence — staff acceptance is required"}
            </div>
            <div className="metrics">
              <div className="metric">
                <span>Local match confidence</span>
                <strong>
                  {Number(d.confidence).toFixed(2)}
                  <small>%</small>
                </strong>
                <Badge value={d.verdict} />
              </div>
              <div className="metric">
                <span>Heuristic risk score</span>
                <strong>
                  {text(risk.score)}
                  <small>/100</small>
                </strong>
                <Badge
                  value={
                    risk.level === "high"
                      ? "HIGH RISK — REVIEW REQUIRED"
                      : risk.level
                  }
                />
              </div>
              <div className="metric">
                <span>Text engine</span>
                <h2>{text(d.ocr_engine)}</h2>
                <p>{text(d.extraction_source)}</p>
              </div>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <h2>Extracted fields</h2>
                <a
                  href={
                    "/api/backend/certificates/" + d.certificate_id + "/file"
                  }
                  download
                >
                  Download source
                </a>
              </div>
              <Table
                rows={Object.entries(d.extracted as Row).map(
                  ([field, value]) => ({ field, value }),
                )}
                columns={[
                  ["field", "Field"],
                  ["value", "Observed in document"],
                ]}
              />
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Heuristic risk signals</h2>
                <span>Heuristic, not validated</span>
              </div>
              <Table
                rows={risk.reasons as Row[]}
                columns={[
                  ["label", "Reason"],
                  ["weight", "Weight"],
                  ["evidence", "Measured evidence"],
                ]}
              />
              <div className="padded">
                <h3>Not assessed</h3>
                <p>{(d.not_assessed as string[]).join(" · ")}</p>
                <p>{(d.warnings as string[]).join(" ")}</p>
              </div>
            </section>
            <Link className="button" href="/certificates">
              New trial
            </Link>
          </>
        ) : null}
      </State>
    </>
  );
}

function CareerScreen({ user }: { user: User }) {
  const [question, setQuestion] = useState("Can I become a Data Scientist?"),
    [result, setResult] = useState<Row | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function send() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await api<Row>("/students/" + user.student_id + "/career", {
          method: "POST",
          body: JSON.stringify({ question }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Title
        eyebrow="EVIDENCE-BASED NEXT STEPS"
        title="Career Copilot"
        description="A deterministic readiness score. Practical steps based on the evidence you have."
      />
      <div className="two-columns career-layout">
        <section className="panel padded">
          <h2>Where do you want to go?</h2>
          <p className="muted">
            Supported roles: Data Scientist, Full Stack Developer, ML Engineer
            and Cloud Engineer.
          </p>
          <label>
            Your question
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={1000}
            />
          </label>
          <button
            className="primary"
            disabled={busy || !question.trim()}
            onClick={send}
          >
            {busy ? "Comparing evidence…" : "Send question"}
            <ArrowRight size={16} />
          </button>
          {error ? (
            <p role="alert" className="error">
              {error}
            </p>
          ) : null}
          {result ? (
            <>
              <div className="notice">
                Deterministic score · {text(result.phrasing_source)}
              </div>
              <p>{text(result.explanation)}</p>
              <h3>Recommended steps</h3>
              {(result.recommended_steps as Row[]).map((s) => (
                <article className="finding" key={text(s.priority)}>
                  <h3>{text(s.action)}</h3>
                  <p>
                    {text(s.reason)} · {text(s.estimated_weeks)} weeks
                  </p>
                </article>
              ))}
            </>
          ) : (
            <div className="empty">
              <GraduationCap />
              <p>Your evidence and next steps will appear here.</p>
            </div>
          )}
        </section>
        <section className="panel padded">
          <div className="eyebrow">ROLE READINESS</div>
          <div className="readiness">
            {result ? text(result.readiness_percent) : "—"}
            <small>%</small>
          </div>
          <p>Matched catalogue weights, out of 100.</p>
          {result ? (
            <>
              <h3>Matched skills</h3>
              <Table
                rows={result.matched_skills as Row[]}
                columns={[
                  ["label", "Skill"],
                  ["weight", "Points"],
                ]}
              />
              <h3>Missing evidence</h3>
              <Table
                rows={result.missing_skills as Row[]}
                columns={[
                  ["label", "Skill"],
                  ["weight", "Points"],
                ]}
              />
            </>
          ) : null}
          <p className="note">
            Self-reported skills add no points. Optional AI cannot change the
            score.
          </p>
        </section>
      </div>
    </>
  );
}

function Oversight() {
  const query = useData<Envelope>("/oversight");
  return (
    <>
      <Title
        eyebrow="AGGREGATE GOVERNANCE"
        title="Institution oversight"
        description="Submission coverage and discrepancies. No raw student records in this view."
      />
      <section className="panel">
        <State {...query} retry={query.reload}>
          <Table
            rows={query.data?.items || []}
            columns={[
              ["institution_name", "Institution"],
              ["state", "State"],
              ["total", "Records"],
              ["submission_percent", "Submitted %"],
              ["missing_records", "Missing"],
              ["unresolved_discrepancies", "Discrepancies"],
              ["pending_reviews", "Pending review"],
            ]}
          />
        </State>
      </section>
      <Link className="button" href="/cases">
        Open masked case queue
      </Link>
    </>
  );
}
function Analytics({ user }: { user: User }) {
  const [kind, setKind] = useState("admissions");
  const [inst, setInst] = useState(
    user.institution_id || user.assigned_institutions[0] || "",
  );
  const institutions = useData<Envelope>("/institutions");
  const query = useData<Envelope>(
    "/analytics/" + kind + (inst ? "?institution_id=" + inst : ""),
    5000,
  );
  const columns: Record<string, [string, string][]> = {
    admissions: [
      ["year", "Cohort"],
      ["program_id", "Program"],
      ["admitted", "Admitted"],
    ],
    placements: [
      ["year", "Graduation year"],
      ["eligible_students", "Eligible students"],
      ["placed_students", "Placed students"],
      ["placement_rate", "Rate %"],
      ["median_package_lpa", "Median LPA"],
      ["max_package_lpa", "Maximum LPA"],
    ],
    performance: [
      ["year", "Year"],
      ["branch", "Branch"],
      ["assessed_students", "Assessed"],
      ["avg_cgpa", "Average CGPA"],
      ["pass_percent", "Pass %"],
    ],
    "data-quality": [
      ["total", "Total"],
      ["clean", "Clean"],
      ["flagged", "Flagged"],
      ["incomplete", "Incomplete"],
      ["submission_percent", "Submission %"],
    ],
  };
  return (
    <>
      <Title
        eyebrow="MEASURED INSTITUTIONAL DATA"
        title="Analytics"
        description="Materialized views with explicit denominators and refresh timestamps."
      >
        <button
          onClick={async () => {
            await api("/analytics/refresh", { method: "POST", body: "{}" });
            query.reload();
          }}
        >
          <RefreshCw size={16} /> Refresh now
        </button>
      </Title>
      <section className="panel">
        <div className="filters">
          <label>
            Institution
            <select value={inst} onChange={(e) => setInst(e.target.value)}>
              <option value="">All authorized institutions</option>
              {institutions.data?.items.map((r) => (
                <option key={text(r.id)} value={text(r.id)}>
                  {text(r.name)}
                </option>
              ))}
            </select>
          </label>
          <label>
            View
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {["admissions", "placements", "performance", "data-quality"].map(
                (k) => (
                  <option key={k}>{k}</option>
                ),
              )}
            </select>
          </label>
        </div>
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <p className="note padded">
                Data as of {text(query.data.data_as_of)} · View query{" "}
                {text(query.data.took_ms)} ms ·{" "}
                {query.data.stale
                  ? "Stale — refresh pending"
                  : "Current source epoch"}
              </p>
              <Table rows={query.data.items} columns={columns[kind]} />
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}
function Architecture() {
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
function DemoControls({ user }: { user: User }) {
  const query = useData<Row>("/demo/config");
  return (
    <>
      <Title
        eyebrow="LOCAL DEMONSTRATION"
        title="Demo controls"
        description="Actual capabilities and owner-only commands."
      />
      <section className="panel padded">
        <State {...query} retry={query.reload}>
          {query.data ? (
            <>
              <Table
                rows={Object.entries(query.data).map(([capability, value]) => ({
                  capability,
                  value,
                }))}
                columns={[
                  ["capability", "Capability"],
                  ["value", "Current state"],
                ]}
              />
              <h2>Local CLI required</h2>
              <p>
                Audit sandbox writes run with owner credentials in your
                terminal. Web processes have no owner credentials or sandbox
                privileges.
              </p>
              <pre>
                python -m app.cli audit-sandbox create --institution-key
                institution_a
              </pre>
              <pre>
                python -m app.cli audit-sandbox tamper --institution-key
                institution_a
              </pre>
              <p>
                Read MORNING.md for environment limits and unverified gates.
              </p>
              <p className="note">
                Current role: {user.role}. No HTTP reset or tamper-write
                endpoint exists.
              </p>
            </>
          ) : null}
        </State>
      </section>
    </>
  );
}

"""Maintain a machine-readable owner register and render its review tables."""

import json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = []


def add(id, priority, what, where, why, fallback, resolve, verify, status="OPEN", options="", variable=None):
    row = dict(
        id=id,
        priority=priority,
        what=what,
        where=where,
        why=why,
        fallback=fallback,
        options=options,
        resolve=resolve,
        verify=verify,
        status=status,
    )
    if variable:
        row["variable"] = variable
    rows.append(row)


add(
    "D1",
    "SHOULD",
    "Host validation uses Python 3.12 and Node 25.",
    "Host toolchain",
    "Installed toolchain differs from container targets.",
    "Native build and tests run on installed versions.",
    "1. Run the Docker target for Python 3.11 and Node 22 reproduction.",
    "docker compose build; successful image builds",
    options="Keep native versions; or use Docker for the specified versions.",
)
decisions = [
    (
        "PGDM uses six trimesters and a 4.0 pass mark.",
        "db/core.sql; db/views.sql",
        "Organizer grading structure is not available.",
        "Synthetic program structure is used.",
        "Keep synthetic assumptions; or migrate mappings after organizer answers.",
    ),
    (
        "Identifiers use the synthetic SYN plus Luhn format.",
        "app/core/algorithms.py",
        "Real APAAR specification is outside the synthetic prototype.",
        "Only synthetic identifiers are accepted.",
        "Keep synthetic mode; or separately implement an approved official adapter.",
    ),
    (
        "Placement rate counts distinct eligible students with best graduation-year offers.",
        "db/views.sql",
        "Organizer denominator needs confirmation.",
        "Specified deterministic denominator is used.",
        "Keep denominator; or revise view definitions and regression fixtures.",
    ),
    (
        "Tesseract is the only image OCR adapter currently implemented.",
        "modules/certificates/service.py",
        "Paddle assets and engine are unavailable.",
        "PDF text works without OCR.",
        "Install Tesseract; or implement and separately test Paddle.",
    ),
    (
        "Cloud bootstrap should use 5,000 students.",
        "docs/deployment.md",
        "The full database exceeds the conservative 400 MB application budget.",
        "Native 100k remains the judging path.",
        "Use 5k; or measure a larger profile with account headroom.",
    ),
    (
        "Pagination uses bounded offsets with exact counts.",
        "app/main.py",
        "Routine implementation choice.",
        "Offset limit 10,000 and page sizes 25 or 50.",
        "Keep bounded offsets; or implement keyset pagination with a changed API.",
    ),
    (
        "Dependencies were resolved at build time and locked.",
        "package-lock.json; requirements.lock",
        "Host versions and container compatibility differ.",
        "Exact resolved dependency versions are recorded.",
        "Use locked versions; or deliberately upgrade and rerun checks.",
    ),
    (
        "Fresh reproduction uses an isolated scratch database.",
        "scripts/reproduce.py",
        "Preserves the active local demonstration.",
        "100k fresh migrations/bootstrap/API run independently.",
        "Use scratch reproduction; or perform the exact clean-checkout Docker rehearsal after backup.",
    ),
    (
        "Most routes and screen composition remain consolidated.",
        "app/main.py; components/workspace.tsx",
        "The exact requested module tree is not yet delivered.",
        "Working service boundaries cover core flows.",
        "Refactor to exact module tree; or accept a smaller implementation with documented limits.",
    ),
    (
        "Baseline grade generation uses deterministic hash distribution.",
        "db/seed/generate.py",
        "This departs from the requested bounded normal distribution.",
        "Credit-weighted CGPA and exact showcase terms remain computed.",
        "Replace with seeded bounded normal generation; or retain this synthetic distribution.",
    ),
    (
        "External deployment is not performed.",
        "render.yaml; docs/deployment.md",
        "Owner accounts, terms and provider secrets are human-only.",
        "Local application and configuration are provided.",
        "Remain local; or configure accounts and verify the cloud preview.",
    ),
]
for i, (what, where, why, fallback, options) in enumerate(decisions, 2):
    add(
        f"D{i}",
        "SHOULD",
        what,
        where,
        why,
        fallback,
        "1. Review the options. 2. If changing the default, update the named implementation and rerun verification.",
        "python scripts/verify_all.py; inspect every recorded failure",
        options=options,
    )

variables = [
    "DATABASE_URL",
    "DATABASE_OWNER_URL",
    "RUNTIME_DB_PASSWORD",
    "JWT_SECRET",
    "MASK_SECRET",
    "GRANT_SECRET",
    "DEMO_PASSWORD",
    "API_INTERNAL_ORIGIN",
    "WEB_ORIGIN",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
]
for i, key in enumerate(variables, 1):
    where = (".env.production.example" if i <= 9 else ".env.example and .env.production.example") + " variable " + key
    add(
        f"P{i}",
        "COULD" if i >= 10 else "SHOULD",
        "Supply the external deployment value for " + key + ".",
        where,
        "Cloud values and optional model account values belong to the owner.",
        "Local .env already has generated secrets and loopback origins.",
        "1. Follow docs/deployment.md. 2. Set "
        + key
        + " directly in the relevant provider or local .env; never commit the value.",
        "python -m app.cli preflight; database ready and intended capabilities listed",
        variable=key,
    )

actions = [
    (
        "Docker Desktop",
        "Docker is absent; Linux container setup needs the owner.",
        "Native PostgreSQL 16 is running.",
        "1. Install Docker Desktop from the official Docker website. 2. Enable Linux containers and launch it. 3. Run the five README Docker commands.",
        "docker compose version; prints a Compose version",
        "READY",
    ),
    (
        "Local secrets",
        "The owner must retain the local generated password privately.",
        "init-env ran and local login was verified.",
        "1. Run .\\scripts\\demo.ps1 init-env. 2. Run .\\scripts\\demo.ps1 show-demo-password locally. 3. Keep .env out of Git. Generated values are POSTGRES_PASSWORD, RUNTIME_DB_PASSWORD, DATABASE_URL, DATABASE_OWNER_URL, JWT_SECRET, MASK_SECRET, GRANT_SECRET and DEMO_PASSWORD.",
        "python -m app.cli preflight; database=true and seed_ready=true",
        "VERIFIED-BY-BUILDER",
    ),
    (
        "Optional Gemini account",
        "An API key and available model require an owner account.",
        "RULE_BASED extraction and career guidance pass without a key.",
        "1. Open Google AI Studio. 2. Create an API key without enabling billing. 3. Paste it into .env GEMINI_API_KEY. 4. Set GEMINI_MODEL to an available model and LLM_ENABLED=true. 5. Restart API. Live account behavior remains unverified.",
        "python -m app.cli preflight; llm_enabled=true and llm_configured=true, then verify a PDF and inspect extraction_source",
        "READY",
    ),
    (
        "Neon project",
        "The owner must create a project and provide SSL connection strings.",
        "Local database only.",
        "1. Create an empty Neon project using PostgreSQL 16. 2. Copy its direct owner URL and pooled runtime URL. 3. Follow the guarded cloud-bootstrap steps in docs/deployment.md with --students 5000. 4. Measure pg_database_size.",
        "python -m app.cli preflight; database=true, seed_ready=true",
        "READY",
    ),
    (
        "Render service",
        "Provisioning and secrets require the owner account.",
        "Local API works.",
        "1. Resolve cloud gaps in V3. 2. Create the Docker web service from render.yaml. 3. Set DATABASE_URL, JWT_SECRET, MASK_SECRET, GRANT_SECRET and WEB_ORIGIN directly in Render. 4. Keep owner URL off the runtime service. 5. Open /api/v1/health/ready and allow cold start time.",
        "Open backend /api/v1/health/ready; HTTP200 ready",
        "BLOCKED",
    ),
    (
        "Vercel project",
        "The owner must import a repository and accept provider terms.",
        "Local Next web app works.",
        "1. Create the private GitHub repository in M7. 2. Import it in Vercel. 3. Set root apps/web and Node22. 4. Set API_INTERNAL_ORIGIN to the Render HTTPS origin, WEB_ORIGIN to the exact Vercel HTTPS origin and COOKIE_SECURE=true. 5. Align backend WEB_ORIGIN.",
        "Open frontend /login and sign in; dashboard loads through same-origin proxy",
        "READY",
    ),
    (
        "Private GitHub repository",
        "Repository creation and pushing are owner-only by the prompt.",
        "Local commits only; no remote is added.",
        "1. Create an empty private repository on GitHub. 2. Copy its SSH or HTTPS URL. 3. Run git remote add origin with that URL locally. 4. Run git push -u origin HEAD.",
        "git remote -v; shows the owner-selected repository without credentials",
        "READY",
    ),
    (
        "Optional tunnel",
        "A tunnel process and laptop availability need owner operation.",
        "Loopback-only demo works.",
        "1. Install cloudflared. 2. Run cloudflared tunnel --url http://localhost:3000. 3. Copy the returned exact HTTPS origin into .env WEB_ORIGIN. 4. Set COOKIE_SECURE=true. 5. Restart API and web with scripts/launch.py. Keep the API port private.",
        "Open tunnel /login; same-origin sign-in and CSRF mutation succeed",
        "READY",
    ),
    (
        "Manual walkthrough",
        "Human visual and keyboard checks remain necessary.",
        "Six scripted browser flows, mobile overflow and axe checks passed.",
        "1. Follow docs/demo-script.md in separate role contexts. 2. Inspect A4 print preview. 3. Inspect 375px layout. 4. Navigate using only Tab, Shift+Tab, Enter and Escape. 5. Enable reduced motion. 6. Inspect palette and focus visibility.",
        "Complete every manual tick box in MORNING.md; no clipping or inaccessible controls",
        "READY",
    ),
    (
        "Laptop benchmark",
        "Latency measurements must be repeated on the actual judging hardware.",
        "Builder measurements are recorded in docs/benchmark-results.json.",
        "1. Activate .venv and start native DB. 2. Run python scripts/benchmark.py --runs 20. 3. Paste the output and hardware details into docs/performance.md.",
        "python scripts/benchmark.py --runs 20; real p50/p95 output with cache equivalence checks",
        "READY",
    ),
    (
        "Real PNG OCR",
        "Tesseract is not installed and Paddle is not implemented.",
        "Text-bearing PDF fixtures verify through PDF_TEXT; images return UNREADABLE when no engine exists.",
        "1. Install Tesseract with English data on the owner machine or run the Docker image. 2. Put tesseract on PATH. 3. Restart API. 4. Upload fixtures/certificates/showcase-genuine.png as Trial and verify it.",
        "python -m app.cli preflight --include-documents; TESSERACT appears, then real PNG report extracts Riya Sharma",
        "READY",
    ),
    (
        "Organizer checklist",
        "The team lead must obtain schema and policy answers.",
        "Synthetic assumptions and mappings remain in force.",
        "1. Read docs/organizer-checklist.md. 2. Send it to the team lead yourself. 3. Request only schema descriptions or synthetic/anonymized examples. 4. Adjust mappings, program terms, grade rules and placement definitions after answers arrive.",
        "Review updated docs/assumptions.md and rerun python scripts/verify_all.py",
        "READY",
    ),
]
for i, (name, why, fallback, steps, verify, status) in enumerate(actions, 1):
    add(
        f"A{i}",
        "SHOULD" if i in [1, 2, 9, 10, 11, 12] else "COULD",
        name,
        f"M{i}; docs/morning-checklist.md",
        why,
        fallback,
        steps,
        verify,
        "VERIFIED-BY-BUILDER" if status == "VERIFIED-BY-BUILDER" else "OPEN",
    )

gaps = [
    (
        "Docker build and runtime are unverified.",
        "docker compose",
        "Docker command is unavailable.",
        "Native PostgreSQL16 path is verified.",
        "Install Docker Desktop and run README five commands.",
        "docker compose build; then readiness200",
    ),
    (
        "Exact repository tree and full router/service/repository split are incomplete.",
        "docs/artifact-check.json",
        "Many specified component/domain files are absent.",
        "Core end-to-end flows run through consolidated modules.",
        "Implement missing modules without empty substitutes, then run the artifact checker.",
        "python scripts/check_artifacts.py; zero missing paths",
    ),
    (
        "Cloud preview requires further implementation and account verification.",
        "docs/deployment.md",
        "Cloud bootstrap, file restoration, wake UI and cloud upload controls are incomplete.",
        "Use the persistent local judging demo.",
        "Finish the cloud-specific gates, create accounts, seed5000, test cookie/CSRF/files.",
        "Run the documented cloud smoke test and record actual URLs and database bytes",
    ),
    (
        "Some mandatory API behavior and idempotency paths are incomplete.",
        "app/main.py",
        "Program quality/oversight filters, web benchmark, HTTP sandbox broker and some mutation replay paths need work.",
        "Supported core API routes return real results; unsupported controls fail explicitly.",
        "Complete operations and tests against section7 of the prompt.",
        "Compare OpenAPI and run the complete operation contract suite",
    ),
    (
        "Seed enrichment and distribution do not fully match the prompt.",
        "db/seed/generate.py",
        "Most enrichment is showcase-only and grade distribution is deterministic hash-based.",
        "100k real relational students, terms, placement rows and showcase evidence are present.",
        "Implement specified cohort allocations, bounded normal grades, child percentages and200+2 certificate subset.",
        "Count all child rows and verify seeded distribution against the prompt",
    ),
    (
        "Optional visual fraud signals and Paddle are not implemented.",
        "modules/certificates/service.py",
        "pHash, ELA, noise, blur, revision/font checks are listed not assessed.",
        "Measured name and metadata checks give the required tampered risk83.",
        "Implement and calibrate supporting checks with fixtures; do not claim real-world accuracy.",
        "Run image and PDF adversarial tests and inspect not_assessed fields",
    ),
    (
        "Full screen-state and accessibility specification is only partially covered.",
        "components/workspace.tsx",
        "Sortable density controls, dialogs, chart views, command palette, history loading and some action flows differ.",
        "Core screens, responsive ledger, mobile overflow and axe pass.",
        "Complete each screen state and keyboard interaction specified in section9.",
        "Run full Playwright flows and manual M9 checklist",
    ),
    (
        "Heavy separate-volume benchmarks and controlled EXPLAIN comparison are incomplete.",
        "scripts/benchmark.py",
        "Current101k measurement exists; separate50k/100k isolated comparison and before/after plans are not delivered.",
        "20 fixed query measurements verify result-cache equivalence.",
        "Implement scripts/explain.py and benchmark the two fixed isolated volumes.",
        "Record actual plans, counts, database bytes and p50/p95 for each volume",
    ),
    (
        "Full adversarial and fresh-checkout audit is incomplete.",
        "docs/audit-passes.md",
        "The exact Section0.6 stopping rule and all specified adversarial scenarios have not yet been completed.",
        "Native schema checks, fresh database API reproduction, fault rehearsal and selected security tests exist.",
        "Finish the omitted scenarios and repeat full cycles with real evidence.",
        "python scripts/verify_all.py --full plus every PassD scenario",
    ),
    (
        "Gemini live account and PNG OCR are unverified.",
        "integrations/gemini.py; M3; M11",
        "No external key/model or local Tesseract engine is available.",
        "Deterministic PDF-text path passes.",
        "Complete optional M3 and M11 on owner hardware.",
        "Inspect actual extraction_source and ocr_engine after real verification",
    ),
    (
        "Hosted CI is unverified.",
        ".github/workflows/ci.yml",
        "No remote repository or hosted workflow run is authorized.",
        "Equivalent local checks are executable.",
        "After M7, run CI on the private repository and inspect logs.",
        "GitHub Actions reports every required check result",
    ),
]
for i, (what, where, why, fallback, resolve, verify) in enumerate(gaps, 1):
    add(f"V{i}", "MUST" if i in [2, 4, 5, 7, 9] else "SHOULD", what, where, why, fallback, "1. " + resolve, verify)
for i, (what, where) in enumerate(
    [
        ("Consolidated module tree remains a reduced deliverable.", "V2"),
        ("Tier2 web benchmark and complete performance drawer are not delivered.", "V4; V8"),
        ("Visual fraud support and Paddle remain off.", "V6"),
        ("Cloud deployment remains unprovisioned.", "V3"),
        ("Some screen controls and state details remain incomplete.", "V7"),
    ],
    1,
):
    add(
        f"S{i}",
        "SHOULD",
        what,
        where,
        "Explicitly recorded unfinished scope.",
        "Core local demo remains usable.",
        "1. Complete the referenced V item and rerun its checks.",
        "Referenced V item passes its verification command.",
    )


def render():
    register = ROOT / "docs/owner-register.json"
    if register.exists():
        previous = json.loads(register.read_text())
        old = {r["id"]: r for r in previous}
        for row in rows:
            if row["id"] in old and old[row["id"]]["status"] != "OPEN":
                row["status"] = old[row["id"]]["status"]
        rows.extend(r for r in previous if r["id"] not in {n["id"] for n in rows})
    register.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    counts = Counter(r["priority"] for r in rows if r["status"] == "OPEN")
    header = f"# Owner decisions\n\nRun start: 2026-10-25T21:23:28+05:30\nRun end: in progress\nEnvironment path: native Windows, PostgreSQL16.15, Python3.12, Node25.\nCounts by type: {dict(Counter(r['id'][0] for r in rows))}\nCounts by status: {dict(Counter(r['status'] for r in rows))}\nOpen priorities: MUST {counts['MUST']}; SHOULD {counts['SHOULD']}; COULD {counts['COULD']}.\nReviewed by owner: [ ]\n\n## START HERE\n\n1. Use README native launch commands to open the existing local demo.\n2. Retrieve the local demo password with scripts/demo.ps1 show-demo-password.\n3. Review the mandatory incomplete items V2, V4, V5, V7 and V9 before treating this as specification-complete.\n4. Follow the manual walkthrough M9.\n5. Install Docker only if reproducing the container path.\n\n"
    columns = ["id", "priority", "what", "where", "why", "fallback", "options", "resolve", "verify", "status"]
    for prefix, title in [
        ("P", "Placeholders"),
        ("D", "Decisions"),
        ("A", "Human-only actions"),
        ("V", "Unverified or blocked"),
        ("S", "Skipped or reduced scope"),
    ]:
        header += f"## {title}\n\n| ID | Priority | What | Where | Why it is waiting | What I did meanwhile | Options and consequences | How to resolve | Verify with | Status |\n|---|---|---|---|---|---|---|---|---|---|\n"
        selected = sorted(
            [r for r in rows if r["id"].startswith(prefix)],
            key=lambda r: ({"MUST": 0, "SHOULD": 1, "COULD": 2}[r["priority"]], int(r["id"][1:])),
        )
        for row in selected:
            header += "| " + " | ".join(str(row[c]).replace("|", "/").replace("\n", " ") for c in columns) + " |\n"
        header += "\n"
    header += "## Superseding implementation notes\n\nOriginal register rows are retained. V4/S2: scoped HTTP benchmarks, result polling, read-only sandbox verification and program/state aggregate fixes are now delivered and regression-tested; remaining API contract coverage stays open. V5: bounded normal grades, credit-weighted CGPAs, cohort allocations, prescribed enrichment ownership, actual certificate subsets and persisted storage manifests are now implemented. A fresh 100k seed validates the principal counts and hashes; full sentence-by-sentence conformance remains open. V8 measurements are retained in performance.md. Seven browser flows now pass. See audit-passes.md for the distinction between automation attempts and complete audit cycles.\n"
    (ROOT / "OWNER_DECISIONS.md").write_text(header, encoding="utf-8")
    checklist = "# Morning checklist\n\nEvery action is also in OWNER_DECISIONS.md. READY means local preparation or documentation is available; it does not claim external verification.\n\n"
    for i, action in enumerate(actions, 1):
        name, why, fallback, steps, verify, status = action
        checklist += f"## M{i} — {name}\n\nStatus: {status}. Owner row A{i}.\n\nWhy human: {why}\n\nSteps: {steps}\n\nVerify: {verify}.\n\nFallback: {fallback}\n\n"
    (ROOT / "docs/morning-checklist.md").write_text(checklist, encoding="utf-8")
    summary = f"[OWNER_DECISIONS.md](OWNER_DECISIONS.md) — open MUST {counts['MUST']}, SHOULD {counts['SHOULD']}, COULD {counts['COULD']}.\n\n"
    summary += "1. Core synthetic local API demo has run end to end.\n2. Native PostgreSQL16 contains the100k baseline plus imported demonstration records.\n3. Exact import and correction counts are measured in docs/acceptance-results.json.\n4. PDF confidence95, tampered risk83, trust91 and readiness74 are computed.\n5. Seven browser flows passed, including375px layout and axe.\n6. Fresh100k database reproduction and schema comparison passed.\n7. Risk1: exact module tree and full response typing remain incomplete.\n8. Risk2: broader screen, seed, API and adversarial requirements remain incomplete.\n9. Risk3: Docker, cloud provisioning, live Gemini and real image OCR remain unverified.\n10. First action: read the incomplete MUST rows, then use README native launch commands.\n\n"
    summary += "## Remaining mandatory work\n\nThis is not a full conformance sign-off. See V2, V4, V5, V7 and V9. Do not describe incomplete or unverified gates as passed.\n\n## Manual walkthrough\n\n- [ ] Use separate Operator, Officer, Admin and Student browser contexts.\n- [ ] Inspect A4 passport print preview for clipping.\n- [ ] Check375px layout and scrollable matrices.\n- [ ] Complete keyboard-only navigation.\n- [ ] Enable reduced motion and inspect focus/contrast.\n- [ ] Rehearse the judging script on the owner laptop.\n\n"
    (ROOT / "MORNING.md").write_text(summary + checklist.split("\n\n", 2)[2], encoding="utf-8")
    print(dict(counts))


if __name__ == "__main__":
    render()

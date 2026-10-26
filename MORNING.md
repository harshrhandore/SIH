[OWNER_DECISIONS.md](OWNER_DECISIONS.md) — open MUST 5, SHOULD 36, COULD 8.

1. Core synthetic local API demo has run end to end.
2. Native PostgreSQL16 contains the100k baseline plus imported demonstration records.
3. Exact import and correction counts are measured in docs/acceptance-results.json.
4. PDF confidence95, tampered risk83, trust91 and readiness74 are computed.
5. Latest browser checks: 14 passed, 0 failed, including375px layout and axe.
6. Fresh100k database reproduction and schema comparison passed.
7. Risk1: exact module tree and full response typing remain incomplete.
8. Risk2: broader screen, seed, API and adversarial requirements remain incomplete.
9. Risk3: Docker, cloud provisioning, live Gemini and real image OCR remain unverified.
10. First action: read the incomplete MUST rows, then use README native launch commands.

## Remaining mandatory work

This is not a full conformance sign-off. See V2, V4, V5, V7 and V9. Do not describe incomplete or unverified gates as passed.

## Manual walkthrough

- [ ] Use separate Operator, Officer, Admin and Student browser contexts.
- [ ] Inspect A4 passport print preview for clipping.
- [ ] Check375px layout and scrollable matrices.
- [ ] Complete keyboard-only navigation.
- [ ] Enable reduced motion and inspect focus/contrast.
- [ ] Rehearse the judging script on the owner laptop.

## M1 — Docker Desktop

Status: READY. Owner row A1.

Why human: Docker is absent; Linux container setup needs the owner.

Steps: 1. Install Docker Desktop from the official Docker website. 2. Enable Linux containers and launch it. 3. Run the five README Docker commands.

Verify: docker compose version; prints a Compose version.

Fallback: Native PostgreSQL 16 is running.

## M2 — Local secrets

Status: VERIFIED-BY-BUILDER. Owner row A2.

Why human: The owner must retain the local generated password privately.

Steps: 1. Run .\scripts\demo.ps1 init-env. 2. Run .\scripts\demo.ps1 show-demo-password locally. 3. Keep .env out of Git. Generated values are POSTGRES_PASSWORD, RUNTIME_DB_PASSWORD, DATABASE_URL, DATABASE_OWNER_URL, JWT_SECRET, MASK_SECRET, GRANT_SECRET and DEMO_PASSWORD.

Verify: python -m app.cli preflight; database=true and seed_ready=true.

Fallback: init-env ran and local login was verified.

## M3 — Optional Gemini account

Status: READY. Owner row A3.

Why human: An API key and available model require an owner account.

Steps: 1. Open Google AI Studio. 2. Create an API key without enabling billing. 3. Paste it into .env GEMINI_API_KEY. 4. Set GEMINI_MODEL to an available model and LLM_ENABLED=true. 5. Restart API. Live account behavior remains unverified.

Verify: python -m app.cli preflight; llm_enabled=true and llm_configured=true, then verify a PDF and inspect extraction_source.

Fallback: RULE_BASED extraction and career guidance pass without a key.

## M4 — Neon project

Status: READY. Owner row A4.

Why human: The owner must create a project and provide SSL connection strings.

Steps: 1. Create an empty Neon project using PostgreSQL 16. 2. Copy its direct owner URL and pooled runtime URL. 3. Follow the guarded cloud-bootstrap steps in docs/deployment.md with --students 5000. 4. Measure pg_database_size.

Verify: python -m app.cli preflight; database=true, seed_ready=true.

Fallback: Local database only.

## M5 — Render service

Status: BLOCKED. Owner row A5.

Why human: Provisioning and secrets require the owner account.

Steps: 1. Resolve cloud gaps in V3. 2. Create the Docker web service from render.yaml. 3. Set DATABASE_URL, JWT_SECRET, MASK_SECRET, GRANT_SECRET and WEB_ORIGIN directly in Render. 4. Keep owner URL off the runtime service. 5. Open /api/v1/health/ready and allow cold start time.

Verify: Open backend /api/v1/health/ready; HTTP200 ready.

Fallback: Local API works.

## M6 — Vercel project

Status: READY. Owner row A6.

Why human: The owner must import a repository and accept provider terms.

Steps: 1. Create the private GitHub repository in M7. 2. Import it in Vercel. 3. Set root apps/web and Node22. 4. Set API_INTERNAL_ORIGIN to the Render HTTPS origin, WEB_ORIGIN to the exact Vercel HTTPS origin and COOKIE_SECURE=true. 5. Align backend WEB_ORIGIN.

Verify: Open frontend /login and sign in; dashboard loads through same-origin proxy.

Fallback: Local Next web app works.

## M7 — Private GitHub repository

Status: READY. Owner row A7.

Why human: Repository creation and pushing are owner-only by the prompt.

Steps: 1. Create an empty private repository on GitHub. 2. Copy its SSH or HTTPS URL. 3. Run git remote add origin with that URL locally. 4. Run git push -u origin HEAD.

Verify: git remote -v; shows the owner-selected repository without credentials.

Fallback: Local commits only; no remote is added.

## M8 — Optional tunnel

Status: READY. Owner row A8.

Why human: A tunnel process and laptop availability need owner operation.

Steps: 1. Install cloudflared. 2. Run cloudflared tunnel --url http://localhost:3000. 3. Copy the returned exact HTTPS origin into .env WEB_ORIGIN. 4. Set COOKIE_SECURE=true. 5. Restart API and web with scripts/launch.py. Keep the API port private.

Verify: Open tunnel /login; same-origin sign-in and CSRF mutation succeed.

Fallback: Loopback-only demo works.

## M9 — Manual walkthrough

Status: READY. Owner row A9.

Why human: Human visual and keyboard checks remain necessary.

Steps: 1. Follow docs/demo-script.md in separate role contexts. 2. Inspect A4 print preview. 3. Inspect 375px layout. 4. Navigate using only Tab, Shift+Tab, Enter and Escape. 5. Enable reduced motion. 6. Inspect palette and focus visibility.

Verify: Complete every manual tick box in MORNING.md; no clipping or inaccessible controls.

Fallback: Six scripted browser flows, mobile overflow and axe checks passed.

## M10 — Laptop benchmark

Status: READY. Owner row A10.

Why human: Latency measurements must be repeated on the actual judging hardware.

Steps: 1. Activate .venv and start native DB. 2. Run python scripts/benchmark.py --runs 20. 3. Paste the output and hardware details into docs/performance.md.

Verify: python scripts/benchmark.py --runs 20; real p50/p95 output with cache equivalence checks.

Fallback: Builder measurements are recorded in docs/benchmark-results.json.

## M11 — Real PNG OCR

Status: READY. Owner row A11.

Why human: Tesseract is not installed and Paddle is not implemented.

Steps: 1. Install Tesseract with English data on the owner machine or run the Docker image. 2. Put tesseract on PATH. 3. Restart API. 4. Upload fixtures/certificates/showcase-genuine.png as Trial and verify it.

Verify: python -m app.cli preflight --include-documents; TESSERACT appears, then real PNG report extracts Riya Sharma.

Fallback: Text-bearing PDF fixtures verify through PDF_TEXT; images return UNREADABLE when no engine exists.

## M12 — Organizer checklist

Status: READY. Owner row A12.

Why human: The team lead must obtain schema and policy answers.

Steps: 1. Read docs/organizer-checklist.md. 2. Send it to the team lead yourself. 3. Request only schema descriptions or synthetic/anonymized examples. 4. Adjust mappings, program terms, grade rules and placement definitions after answers arrive.

Verify: Review updated docs/assumptions.md and rerun python scripts/verify_all.py.

Fallback: Synthetic assumptions and mappings remain in force.


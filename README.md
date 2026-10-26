# Shiksham APAAR

A synthetic academic ledger for the SIH 26263 specification, built with Next.js, FastAPI and PostgreSQL 16. It includes scoped accounts, student search, imports, correction and review, audit history, academic passports, local certificate checks and career guidance.

**Synthetic data only. This is not an official APAAR service or a production identity-verification system.** Remaining implementation and verification gaps are recorded in [OWNER_DECISIONS.md](OWNER_DECISIONS.md) and [MORNING.md](MORNING.md). No cloud account or Gemini API key is needed to run locally.

## Run locally on Windows

Use this native Windows route for the locally verified setup. All commands below run in **PowerShell from the repository root**, the folder containing `package.json`, `apps` and `scripts`.

### 1. Install prerequisites and clone

Install Git, Python 3.12, Node.js with npm, and portable PostgreSQL 16 Windows binaries. The container target uses Node.js 22; the recorded native build used Node.js 25. See the [verification report](docs/verification-report.md) for the measured environment.

```powershell
git clone https://github.com/harshrhandore/SIH.git
cd SIH
```

Download the PostgreSQL 16 binary archive using the [PostgreSQL Windows download page](https://www.postgresql.org/download/windows/), then extract it inside this repository so these files exist:

```text
.local/
  pgsql/
    bin/
      initdb.exe
      pg_ctl.exe
      psql.exe
      createdb.exe
```

The native database script uses this exact location. An existing PostgreSQL installation elsewhere is not automatically selected.

### 2. Install project dependencies

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements.lock -r apps/api/requirements-dev.lock
npm ci
```

These commands use the virtual environment directly, so activating it or changing PowerShell's execution policy is unnecessary.

### 3. Create the local environment

```powershell
.\.venv\Scripts\python.exe scripts/demo.py init-env --native
```

This generates the local `.env`, database passwords, token secrets and demo password. For native development, the generated database URLs use `127.0.0.1:55432`; the web app uses port `3000` and the API uses port `8000`.

The script preserves an existing `.env`. If it was created for Docker, check that both database URLs point to the native database before proceeding. Keep the generated credentials private.

### 4. Start PostgreSQL and seed the database

```powershell
.\.venv\Scripts\python.exe scripts/native_db.py
$env:PYTHONPATH="$PWD\apps\api;$PWD"
.\.venv\Scripts\python.exe -m app.cli bootstrap --students 100000
.\.venv\Scripts\python.exe -m app.cli preflight
```

The database script initializes the project-local cluster if necessary, starts PostgreSQL and creates the database. Bootstrap applies migrations and loads the synthetic records and certificate fixtures. Wait for bootstrap to finish before starting the app.

For a smaller first-time dataset, use `--students 5000` instead. The documented full demo and performance checks use `100000`. Bootstrap leaves an already seeded database unchanged; changing the option does not resize an existing dataset.

Preflight should report `"database": true` and `"seed_ready": true`. OCR and model capabilities depend on the optional tools configured on your machine.

### 5. Start the API and web app

Keep two PowerShell terminals open in the repository root.

**Terminal 1 — API:**

```powershell
.\.venv\Scripts\python.exe scripts/launch.py api
```

**Terminal 2 — web app:**

```powershell
.\.venv\Scripts\python.exe scripts/launch.py web
```

Open **[http://localhost:3000/login](http://localhost:3000/login)**.

Use `localhost` consistently in the browser: the default allowed web origin is `http://localhost:3000`.

| Service | Local address |
|---|---|
| Web app | http://localhost:3000/login |
| API readiness | http://127.0.0.1:8000/api/v1/health/ready |
| API documentation | http://127.0.0.1:8000/docs |
| PostgreSQL | 127.0.0.1:55432 |

### 6. Sign in with a demo account

Display the generated password **on your own machine**:

```powershell
.\.venv\Scripts\python.exe scripts/demo.py show-demo-password
```

All five synthetic accounts use that generated demo password.

| Role | Email | Scope |
|---|---|---|
| Operator A | operator.a@example.test | Institution A |
| Operator B | operator.b@example.test | Institution B |
| Verification officer | officer@example.test | Assigned institutions |
| Administrator | admin@example.test | Aggregates and masked cases; raw escalated cases require a grant |
| Student | student.riya@example.test | Riya's own record |

The optional **Demo accounts** section on the login page fills the email address. Enter the password yourself.

Start with the institution ledger or student passport, then follow [the demo walkthrough](docs/demo-script.md) for import, correction, review, certificate and career flows. A fresh seed contains the baseline; a database used for rehearsals may already contain the imported and corrected demonstration batch.

## Start again after the initial setup

Dependencies, environment generation and seeding are first-time setup steps. For later sessions:

```powershell
# Start the existing local database.
.\.venv\Scripts\python.exe scripts/native_db.py

# Terminal 1:
.\.venv\Scripts\python.exe scripts/launch.py api

# Terminal 2:
.\.venv\Scripts\python.exe scripts/launch.py web
```

Open http://localhost:3000/login. Stop the API and web app with **Ctrl+C** in their terminals. To stop the project-local PostgreSQL cluster afterward:

```powershell
.\.local\pgsql\bin\pg_ctl.exe -D .local/pgdata stop -m fast
```

Normal startup preserves the database and uploaded files.

## Docker alternative

The Docker configuration is provided for PostgreSQL 16, Python 3.11 and Node.js 22. **This path was not executed in the recorded native environment because Docker was unavailable.**

Install Docker with Compose and start Docker Desktop in Linux-container mode. From the repository root, generate the environment using Python, then build and start:

```powershell
python scripts/demo.py init-env
docker compose build
docker compose up -d db
docker compose run --rm bootstrap python -m app.cli bootstrap --students 100000
docker compose up -d api web
```

Open http://localhost:3000/login. Run `python scripts/demo.py show-demo-password` locally to retrieve the password.

Compose builds container database URLs from the generated secrets, so an existing native `.env` can be retained. For subsequent starts, use `docker compose up -d db api web`. To stop, use `docker compose down`; named database and storage volumes remain.

On Linux, if bootstrap cannot write the bind-mounted fixture directory, set its ownership from this repository with `sudo chown -R 10001:10001 ./fixtures`, then retry bootstrap.

## Verify the installation

With native PostgreSQL, the API and web app running:

```powershell
$env:PYTHONPATH="$PWD\apps\api;$PWD"
.\.venv\Scripts\python.exe -m app.cli preflight
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

For the automated suite, install the browser binary and ensure npm's Python subprocesses use the project virtual environment:

```powershell
$env:PATH="$PWD\.venv\Scripts;$env:PATH"
$env:PYTHONPATH="$PWD\apps\api;$PWD"
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.local\browsers"
npx playwright install chromium
python scripts/verify_all.py
```

The full sweep includes an isolated 100,000-student database reproduction in `shiksham_repro`, tests, lint, type checks, build, generated-client checks, browser flows, artifact checks and benchmarks. It can take time and requires owner database access. Inspect every result in `docs/verification-results.json`; remaining specification gaps can cause gates to fail.

## Troubleshooting

| Problem | What to check |
|---|---|
| `py` is not recognized | Install Python 3.12 with the Windows launcher, or use your Python 3.12 executable in the venv creation command. |
| `npm` is not recognized | Install Node.js, reopen PowerShell and run `npm --version`. |
| `pg_ctl.exe` or `initdb.exe` is missing | Check the extraction path: `.local/pgsql/bin/`. Avoid an extra nested `pgsql` directory. |
| Database connection fails | Run `scripts/native_db.py`; check port `55432` and both database URLs in your private `.env`. |
| Port `3000` or `8000` is occupied | Stop the conflicting development server, then restart the corresponding launcher. |
| Login or mutations return an origin error | Open `http://localhost:3000`; check `WEB_ORIGIN=http://localhost:3000` and `COOKIE_SECURE=false` for local HTTP, then restart both launchers after environment changes. |
| Login fails | Retrieve the generated demo password and use an email from the account table. Repeated failed logins are rate-limited. |
| Python reports a missing module | Use `.venv/Scripts/python.exe` and install both locked requirements files. For npm schema generation, put the venv on `PATH` as shown above. |
| Image OCR is unavailable | Text-bearing PDFs work without an OCR engine. PNG/JPEG text extraction requires optional Tesseract; see the morning checklist. |
| Gemini is not configured | Leave the model feature disabled; deterministic local extraction and career guidance are available. |

## Further documentation

- [Demo walkthrough](docs/demo-script.md)
- [Morning checklist](MORNING.md) and [owner decisions](OWNER_DECISIONS.md)
- [Architecture](docs/architecture.md) and [algorithms](docs/algorithms.md)
- [Security boundaries](docs/security.md)
- [Deployment guide](docs/deployment.md)
- [Verification report](docs/verification-report.md)
- [UI audit](docs/ui-audit/README.md)

The local `.env`, `.venv`, PostgreSQL binaries, database cluster and stored uploads are not supplied by cloning the repository; the setup steps create or install them.

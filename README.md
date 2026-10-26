# Shiksham APAAR

A synthetic academic ledger built from the supplied SIH 26263 specification. The measured local demo supports scoped login, 100,000 students, search, 1,000-row import, correction and review, audit history, passport, PDF-text certificate checks and deterministic career guidance.

**Start with [MORNING.md](MORNING.md) and [OWNER_DECISIONS.md](OWNER_DECISIONS.md).** This repository is a working local implementation with remaining specification gaps recorded there. It is not a production identity-verification system.

The current Windows installation is ready to run from this directory. PostgreSQL binaries and its isolated data directory are under ignored `.local/`; Python dependencies are under ignored `.venv/`. No account, cloud subscription or Gemini key is needed for the local demo.

```powershell
.\.venv\Scripts\python.exe scripts/native_db.py
# Terminal 1
.\.venv\Scripts\python.exe scripts/launch.py api
# Terminal 2
.\.venv\Scripts\python.exe scripts/launch.py web
```

Open http://localhost:3000/login. Retrieve the password locally:

```powershell
.\scripts\demo.ps1 show-demo-password
```

Sign in with your account email and the demo password. The optional **Demo accounts** section on the login page lists all five synthetic accounts and fills in the email when selected. Operator A and B are institution-scoped; the officer is assigned to the synthetic institutions; the administrator receives aggregates and masked cases; the student can see only their own record. Architecture and demo utilities are available directly at `/architecture` and `/settings/demo`, outside the workspace navigation. The rehearsal has already imported and corrected the demo batch in the active database, so the current ledger is the post-correction state. Read [demo-script.md](docs/demo-script.md) before presenting.

For a new native checkout, install Python 3.12 and Node, create a venv, install `apps/api/requirements.lock` and `requirements-dev.lock`, run `npm ci`, run `scripts/demo.py init-env --native`, extract PostgreSQL 16 Windows binaries to `.local/pgsql`, run `scripts/native_db.py`, then use `python -m app.cli bootstrap --students 100000` with `PYTHONPATH` containing `apps/api` and the repository root. The portable PostgreSQL package is provided by [EDB through PostgreSQL's Windows download page](https://www.postgresql.org/download/windows/). The owner's machine has already completed these steps.

The requested Docker path is prepared but could not be executed because Docker is absent:

```powershell
.\scripts\demo.ps1 init-env
docker compose build
docker compose up -d db
docker compose run --rm bootstrap python -m app.cli bootstrap --students 100000
docker compose up -d api web
```

Compose constructs container database URLs from the generated component secrets, so the existing native `.env` can remain in place. Linux bind-mount fixture ownership, if needed: `sudo chown -R 10001:10001 ./fixtures` from this repository only. No reset runs on normal startup. There is no HTTP reset endpoint.

Activate the venv before npm schema-generation commands:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="$PWD\apps\api;$PWD"
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.local\browsers"
python scripts/verify_all.py
# Includes a fresh isolated 100k database rehearsal:
python scripts/verify_all.py --full
```

The verification sweep always reproduces an allowlisted scratch database, `shiksham_repro`, preserving the active demo. This verifies fresh migrations/bootstrap/API behavior; it does not prove the specification's exact clean-checkout, deleted-environment Docker workflow. Scripts never print local secrets during verification. For an intentional active-demo reset, see the guarded backup-and-reset command in the demo script.

Read the [architecture](docs/architecture.md), [algorithms](docs/algorithms.md), [security boundaries](docs/security.md), [deployment guide](docs/deployment.md), [demo script](docs/demo-script.md), and [verification report](docs/verification-report.md). Raw evidence is in `docs/acceptance-results.json`, `benchmark-results.json`, `schema-check.json`, `reproduction-results.json` and `playwright-results.json`.

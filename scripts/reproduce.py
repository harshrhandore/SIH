"""Reproduce bootstrap + full API demo in an isolated, fixed-name database."""

import json, os, subprocess, sys
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from check_schema import database_url

ROOT = Path(__file__).resolve().parents[1]
values = dotenv_values(ROOT / ".env")
owner = values["DATABASE_OWNER_URL"]
with psycopg.connect(database_url(owner, "postgres"), autocommit=True) as c:
    c.execute("DROP DATABASE IF EXISTS shiksham_repro WITH (FORCE)")
    c.execute("CREATE DATABASE shiksham_repro")
env = {
    **os.environ,
    "PYTHONPATH": os.pathsep.join([str(ROOT / "apps/api"), str(ROOT)]),
    "DATABASE_OWNER_URL": database_url(owner, "shiksham_repro"),
    "DATABASE_URL": database_url(values["DATABASE_URL"], "shiksham_repro"),
    "STORAGE_ROOT": str(ROOT / "storage/repro"),
}
results = []
for command in [
    [sys.executable, "-m", "app.cli", "bootstrap", "--students", "100000"],
    [sys.executable, "scripts/acceptance.py"],
]:
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr if result.returncode else "")
    results.append(
        dict(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr if result.returncode else "",
        )
    )
    if result.returncode:
        break
(ROOT / "docs/reproduction-results.json").write_text(json.dumps(results, indent=2))
raise SystemExit(results[-1]["exit_code"])

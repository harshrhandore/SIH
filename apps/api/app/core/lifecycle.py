"""Owner-only lifecycle operations. No HTTP route imports these functions."""

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from psycopg.conninfo import conninfo_to_dict
from app.settings import ROOT, settings
from app.db.session import connect, one, many
from app.core.files import root_path, contained


def local_connection(url):
    parsed = urlparse(url)
    if (
        parsed.query
        or parsed.fragment
        or any(os.getenv(k) for k in ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
    ):
        raise RuntimeError("Connection overrides are not permitted for local lifecycle operations.")
    try:
        effective = conninfo_to_dict(url)
    except Exception:
        raise RuntimeError("Unsupported local connection URL.") from None
    if (
        effective.get("host") not in {"db", "localhost", "127.0.0.1"}
        or effective.get("hostaddr")
        or effective.get("service")
    ):
        raise RuntimeError("Connection is not an approved local target.")
    return parsed, effective


def validate_reset_target(url, target, confirmation):
    parsed, effective = local_connection(url)
    if not settings.demo_mode or parsed.hostname not in {"db", "localhost", "127.0.0.1"}:
        raise RuntimeError("Reset is restricted to local synthetic demo databases.")
    if (
        target != "shiksham"
        or parsed.path != "/shiksham"
        or effective.get("dbname") != "shiksham"
        or confirmation != "RESET-SYNTHETIC-DEMO"
    ):
        raise RuntimeError("Exact target and reset confirmation are required.")
    return parsed


def reset(owner_url, target, confirmation, students):
    parsed = validate_reset_target(owner_url, target, confirmation)
    base = root_path(settings.storage_root).resolve()
    if base not in {(ROOT / "storage").resolve(), Path("/storage").resolve()}:
        raise RuntimeError("Storage reset root is not allowlisted.")
    with connect(owner_url) as conn:
        institutions = many(conn, "SELECT id,aicte_code FROM public.institutions")
        if not institutions or any(not r["aicte_code"].startswith("SYN-") for r in institutions):
            raise RuntimeError("Reset refused: institution codes are not exclusively synthetic.")
        if one(conn, "SELECT 1 FROM public.users WHERE email NOT LIKE '%%@example.test' LIMIT 1"):
            raise RuntimeError("Reset refused: non-synthetic account detected.")
        if one(conn, "SELECT 1 FROM public.students WHERE apaar_id IS NOT NULL AND apaar_id NOT LIKE 'SYN-%%' LIMIT 1"):
            raise RuntimeError("Reset refused: canonical identifiers are not synthetic.")
    dump = shutil.which("pg_dump")
    local = ROOT / ".local/pgsql/bin/pg_dump.exe"
    if not dump and local.exists():
        dump = str(local)
    if not dump:
        raise RuntimeError("pg_dump is required to create the automatic backup before reset.")
    backup = contained(base, "backups/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sql")
    backup.parent.mkdir(parents=True, exist_ok=True)
    command = [
        dump,
        "--host",
        parsed.hostname,
        "--port",
        str(parsed.port or 5432),
        "--username",
        unquote(parsed.username or ""),
        "--dbname",
        "shiksham",
        "--no-password",
        "--file",
        str(backup),
    ]
    subprocess.run(
        command, check=True, env={**os.environ, "PGPASSWORD": unquote(parsed.password or "")}, capture_output=True
    )
    if backup.stat().st_size < 100:
        raise RuntimeError("Backup validation failed; reset refused.")
    print(f"Backup created. Resetting synthetic database host={parsed.hostname}, database=shiksham.")
    # Resolve every recursive-delete target before changing the database or filesystem.
    targets = [contained(base, str(row["id"])) for row in institutions]
    if any(p.parent != base or not p.is_relative_to(base) for p in targets):
        raise RuntimeError("Storage containment check failed.")
    with connect(owner_url) as conn:
        conn.execute("DROP SCHEMA IF EXISTS demo_sandbox CASCADE")
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public AUTHORIZATION shiksham_owner")
    for path in targets:
        if path.exists():
            shutil.rmtree(path)
    from app.cli import bootstrap

    bootstrap(students)


def cloud_bootstrap(owner_url, students, confirmation):
    parsed = urlparse(owner_url)
    options = parse_qs(parsed.query, keep_blank_values=True)
    if (
        set(options) - {"sslmode", "channel_binding"}
        or parsed.fragment
        or any(os.getenv(k) for k in ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
    ):
        raise RuntimeError("Cloud connection target overrides are not permitted.")
    if not settings.demo_mode or students != 5000 or confirmation != "EMPTY-SYNTHETIC-CLOUD":
        raise RuntimeError("Cloud bootstrap requires demo mode, exactly5000students and explicit confirmation.")
    effective = conninfo_to_dict(owner_url)
    if (
        not (parsed.hostname or "").endswith(".neon.tech")
        or effective.get("host") != parsed.hostname
        or options.get("sslmode")
        not in [
            ["require"],
            ["verify-full"],
        ]
    ):
        raise RuntimeError("Cloud bootstrap requires an owner-selected Neon SSL URL.")
    with connect(owner_url) as conn:
        if one(
            conn,
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','m') LIMIT 1",
        ):
            raise RuntimeError("Cloud bootstrap refuses any existing business tables. It never resets remote data.")
    from app.cli import bootstrap

    bootstrap(students)
    with connect(owner_url) as conn:
        size = one(conn, "SELECT pg_database_size(current_database()) AS bytes")["bytes"]
        print(f"Cloud database size: {size} bytes; conservative application budget400000000bytes.")
        if size >= 400000000:
            raise RuntimeError("Cloud database exceeds the conservative budget; do not deploy this profile.")

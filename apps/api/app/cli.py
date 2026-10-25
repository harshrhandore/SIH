import argparse
import json
import os
import shutil
from time import perf_counter
from dotenv import dotenv_values
from psycopg import sql
from alembic.config import Config
from alembic import command
from app.db.session import connect, one
from app.settings import ROOT, settings
from app.core.audit import verify


def owner_url():
    return os.getenv("DATABASE_OWNER_URL") or dotenv_values(ROOT / ".env")["DATABASE_OWNER_URL"]


def migrate():
    config = Config(str(ROOT / "apps/api/alembic.ini"))
    command.upgrade(config, "head")


def bootstrap(students):
    if students not in {200, 5000, 50000, 100000}:
        raise RuntimeError("Unsupported synthetic seed profile.")
    start = perf_counter()
    migrate()
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    with connect(owner_url()) as conn:
        ready = one(conn, "SELECT seed_ready FROM app_state")["seed_ready"]
        if ready:
            print("Already seeded; no changes made.")
            return
        if one(conn, "SELECT count(*) AS n FROM students")["n"]:
            raise RuntimeError("Nonempty target refused. Use documented owner-only reset after backup.")
        if not one(conn, "SELECT 1 FROM pg_roles WHERE rolname='shiksham_runtime'"):
            conn.execute(
                sql.SQL("CREATE ROLE shiksham_runtime LOGIN PASSWORD {}").format(
                    sql.Literal(values["RUNTIME_DB_PASSWORD"])
                )
            )
        conn.execute((ROOT / "db/privileges.sql").read_text())
        from db.seed.generate import seed

        manifest = seed(conn, students, values["DEMO_PASSWORD"])
        from app.modules.certificates.service import seed_certificates

        seed_certificates(conn)
        from db.seed.validate import validate_seed

        manifest["seed_validation"] = validate_seed(conn, students)
        conn.execute("SELECT refresh_demo_views()")
        conn.execute("ANALYZE")
        actual = one(conn, "SELECT count(*) AS n FROM students")["n"]
        if actual != students:
            raise RuntimeError("Seed count mismatch")
        for row in conn.execute("SELECT id FROM institutions").fetchall():
            if not verify(conn, row["id"])["valid"]:
                raise RuntimeError("Seed audit chain invalid")
        conn.execute("UPDATE app_state SET seed_ready=true,updated_at=now()")
        manifest["database_bytes"] = one(conn, "SELECT pg_database_size(current_database()) AS bytes")["bytes"]
        manifest["total_seconds"] = round(perf_counter() - start, 3)
    (ROOT / "fixtures/manifest.json").write_text(json.dumps(manifest, indent=2))
    from app.core.files import root_path, contained

    storage_manifest = contained(root_path(settings.storage_root), "manifest.json")
    storage_manifest.parent.mkdir(parents=True, exist_ok=True)
    storage_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["dataset_students", "seed_seconds", "total_seconds", "database_bytes"]}))


def sandbox(action):
    if not settings.demo_controls_enabled:
        raise RuntimeError("Demo controls disabled")
    from db.seed.fixtures import uid

    inst = uid("institution", 0)
    with connect(owner_url()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if action in {"create", "restore"}:
            conn.execute("CREATE SCHEMA IF NOT EXISTS demo_sandbox")
            conn.execute("DROP TABLE IF EXISTS demo_sandbox.audit_events,demo_sandbox.audit_chains")
            conn.execute(
                "CREATE TABLE demo_sandbox.audit_chains AS SELECT * FROM public.audit_chains WHERE institution_id=%s",
                (inst,),
            )
            conn.execute(
                "CREATE TABLE demo_sandbox.audit_events AS SELECT * FROM public.audit_events WHERE institution_id=%s",
                (inst,),
            )
        elif action == "tamper":
            row = one(
                conn,
                "SELECT * FROM demo_sandbox.audit_events WHERE action='REVIEW_APPROVED' ORDER BY sequence_no DESC LIMIT 1",
            )
            if not row:
                raise RuntimeError("Create sandbox after a review approval")
            parsed = json.loads(row["canonical_text"])
            parsed["reason"] = "TAMPERED SYNTHETIC DEMO"
            from app.core.audit import canonical

            conn.execute(
                "UPDATE demo_sandbox.audit_events SET reason=%s,canonical_text=%s WHERE chain_id=%s AND sequence_no=%s",
                (parsed["reason"], canonical(parsed), row["chain_id"], row["sequence_no"]),
            )
        print(json.dumps(verify(conn, inst, True), default=str))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["bootstrap", "migrate", "preflight", "audit-sandbox", "reset", "cloud-bootstrap"]
    )
    parser.add_argument("action", nargs="?", choices=["create", "restore", "tamper"])
    parser.add_argument("--students", type=int, choices=[200, 5000, 50000, 100000], default=100000)
    parser.add_argument("--institution-key", choices=["institution_a"], default="institution_a")
    parser.add_argument("--include-documents", action="store_true")
    parser.add_argument("--target")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    if args.command == "reset":
        from app.core.lifecycle import reset

        reset(owner_url(), args.target, args.confirm, args.students)
    elif args.command == "cloud-bootstrap":
        from app.core.lifecycle import cloud_bootstrap

        cloud_bootstrap(owner_url(), args.students, args.confirm)
    elif args.command == "bootstrap":
        bootstrap(args.students)
    elif args.command == "migrate":
        migrate()
    elif args.command == "audit-sandbox":
        sandbox(args.action)
    else:
        with connect() as conn:
            print(
                json.dumps(
                    dict(
                        database=bool(one(conn, "SELECT 1 AS ok")),
                        seed_ready=one(conn, "SELECT seed_ready FROM app_state")["seed_ready"],
                        ocr=["PDF_TEXT"] + (["TESSERACT"] if shutil.which("tesseract") else []),
                        llm_enabled=settings.llm_enabled,
                        llm_configured=bool(settings.gemini_api_key and settings.gemini_model),
                    )
                )
            )


if __name__ == "__main__":
    main()

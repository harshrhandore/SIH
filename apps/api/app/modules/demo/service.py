"""Demo HTTP operations."""

from app.modules.demo import repository
from app.core.http import idem
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import Request, BackgroundTasks
from fastapi.responses import FileResponse
from psycopg.types.json import Jsonb
from app.settings import settings, ROOT
from app.db.session import connect
from app.core.errors import fail
from app.core.security import allow, scope_ids, institution_scope
from app.core.rate_limit import limit
from app.core.cache import preferences
from app.core.files import contained, root_path
from app.core.audit import verify
from app.modules.demo.schemas import SessionControls
from app.modules.demo.schemas import BenchmarkRequest


def demo_config(user=None):
    if not settings.demo_mode:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        return dict(
            synthetic=True,
            demo_as_of=settings.demo_as_of,
            controls_enabled=settings.demo_controls_enabled,
            cache_enabled_for_session=preferences.get(str(user["sid"])) is not False,
            llm_enabled=bool(settings.llm_enabled and settings.gemini_api_key and settings.gemini_model),
            ocr_engines=["PDF_TEXT"],
            dataset_students=repository.demo_config_students(conn, ())["n"],
            natural_language_search_enabled=False,
        )


def demo_manifest(user=None):
    if not settings.demo_mode:
        fail("NOT_FOUND", 404)
    data = json.loads((ROOT / "fixtures/manifest.json").read_text())
    keys = [
        "showcase_student_id",
        "showcase_apaar_id",
        "fixture_import",
        "expected_import",
        "correction_row",
        "correct_to",
        "institution_a_id",
        "showcase_readiness",
        "showcase_trust",
    ]
    if user["role_code"] == "ADMIN":
        keys = ["expected_import", "correction_row"]
    if user["role_code"] == "STUDENT" or (
        user["role_code"] == "OPERATOR" and str(user["institution_id"]) != data["institution_a_id"]
    ):
        keys = (
            ["showcase_student_id", "showcase_apaar_id"]
            if str(user.get("student_id")) == data["showcase_student_id"]
            else []
        )
    return {k: data[k] for k in keys}


FIXTURES = {
    "import_csv": "demo-import-1000.csv",
    "import_xlsx": "demo-import-1000.xlsx",
    "genuine_pdf": "certificates/showcase-genuine.pdf",
    "tampered_pdf": "certificates/showcase-tampered.pdf",
    "genuine_png": "certificates/showcase-genuine.png",
}


def fixture(fixture_key: str, user=None):
    if not settings.demo_mode or fixture_key not in FIXTURES:
        fail("NOT_FOUND", 404)
    allow(user, "OPERATOR", "OFFICER", "STUDENT")
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
    if fixture_key.startswith("import"):
        allow(user, "OPERATOR", "OFFICER")
        if manifest["institution_a_id"] not in {str(x) for x in scope_ids(user)}:
            fail("NOT_FOUND", 404)
    elif user["role_code"] == "STUDENT" and str(user["student_id"]) != manifest["showcase_student_id"]:
        fail("NOT_FOUND", 404)
    elif user["role_code"] != "STUDENT" and manifest["institution_a_id"] not in {str(x) for x in scope_ids(user)}:
        fail("NOT_FOUND", 404)
    path = contained(root_path(settings.fixtures_root), FIXTURES[fixture_key])
    return FileResponse(path, filename=path.name)


def sandbox_status(institution_id: UUID, user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    institution_scope(user, institution_id, admin=True)
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        result = verify(conn, institution_id, sandbox=True)
        if not result["exists"]:
            fail("SANDBOX_NOT_INITIALIZED", 404, "Create the isolated copy with the owner-only CLI first.")
        return result


def session_controls(body: SessionControls, user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    preferences.put(str(user["sid"]), body.cache_enabled)
    return dict(
        cache_enabled=body.cache_enabled,
        scope="current_session",
        note="Search preference is scoped to this refresh family.",
    )


def performance(user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        indexes = repository.performance_pg_indexes(conn, ())
    path = ROOT / "docs/benchmark-results.json"
    return dict(
        indexes=indexes,
        before_explain=None,
        after_explain=None,
        benchmark=json.loads(path.read_text()) if path.exists() else None,
        cache_semantics="Application cold bypasses result cache only; database buffers remain warm.",
    )


def web_benchmark(body: BenchmarkRequest, request: Request, tasks: BackgroundTasks, user=None):
    allow(user, "ADMIN", "OFFICER")
    if not settings.demo_mode or not settings.local_benchmark_enabled or (not settings.demo_controls_enabled):
        fail("NOT_FOUND", 404)
    if body.dataset != "current" or body.cache_mode != "BOTH":
        fail("INVALID_BENCHMARK_OPTIONS")
    from app.core.lifecycle import local_connection

    try:
        local_connection(settings.database_url)
    except RuntimeError:
        fail("NOT_FOUND", 404)
    created = False
    with connect() as conn:

        def work(key):
            nonlocal created
            repository.work_query(conn, ())
            if repository.work_benchmark_runs(conn, ()):
                fail("BENCHMARK_RUNNING", 409)
            limit(("benchmark", str(user["id"])), 1, 60)
            run = uuid4()
            repository.work_benchmark_runs_2(conn, (run, user["id"]))
            created = True
            return dict(run_id=run, status="RUNNING", poll_url=f"/api/v1/demo/benchmarks/{run}")

        result = idem(conn, user, request, body.model_dump(), work)

    def execute_benchmark(run_id):
        from scripts.benchmark import benchmark

        try:
            measured = benchmark(body.runs, requester_id=user["id"])
            with connect() as conn:
                measured["query_samples"] = measured.pop("samples")
                measured["samples"] = body.runs
                measured.update(samples_count=body.runs, measured_at=str(datetime.now(timezone.utc)))
                repository.execute_benchmark_benchmark_runs(conn, (Jsonb(measured), run_id))
        except Exception:
            with connect() as conn:
                repository.execute_benchmark_benchmark_runs_2(conn, (Jsonb({"error": "BENCHMARK_FAILED"}), run_id))

    if created:
        tasks.add_task(execute_benchmark, result["run_id"])
    return result


def benchmark_result(run_id: UUID, user=None):
    allow(user, "ADMIN", "OFFICER")
    if not settings.demo_mode or not settings.local_benchmark_enabled or (not settings.demo_controls_enabled):
        fail("NOT_FOUND", 404)
    from app.core.lifecycle import local_connection

    try:
        local_connection(settings.database_url)
    except RuntimeError:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        row = repository.benchmark_result_benchmark_runs(conn, (run_id,))
        if not row:
            fail("NOT_FOUND", 404)
        if user["role_code"] == "OFFICER" and row["requested_by"] != user["id"]:
            fail("NOT_FOUND", 404)
        row.pop("requested_by")
        return {**row, **(row.get("result") or {})}

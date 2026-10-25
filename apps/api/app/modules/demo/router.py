"""Demo HTTP operations."""

from app.core.http import idem
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import Request, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from psycopg.types.json import Jsonb
from app.settings import settings, ROOT
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, scope_ids, institution_scope
from app.core.rate_limit import limit
from app.core.cache import preferences
from app.core.files import contained, root_path
from app.core.audit import verify
from app.modules.demo.schemas import SessionControls
from app.modules.demo.schemas import BenchmarkRequest
from fastapi import APIRouter

router = APIRouter(tags=["demo"])


@router.get("/demo/config")
def demo_config(user=Depends(authenticated)):
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
            dataset_students=one(conn, "SELECT count(*) AS n FROM students")["n"],
            natural_language_search_enabled=False,
        )


@router.get("/demo/manifest")
def demo_manifest(user=Depends(authenticated)):
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
    if (
        user["role_code"] == "STUDENT"
        or user["role_code"] == "OPERATOR"
        and str(user["institution_id"]) != data["institution_a_id"]
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


@router.get("/demo/fixtures/{fixture_key}")
def fixture(fixture_key: str, user=Depends(authenticated)):
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


@router.get("/demo/audit-sandbox")
@router.get("/demo/audit-sandbox/verify")
def sandbox_status(institution_id: UUID, user=Depends(authenticated)):
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


@router.put("/demo/session-controls")
def session_controls(body: SessionControls, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    # Preference is bound to the active refresh family, never a global switch.
    preferences.put(str(user["sid"]), body.cache_enabled)
    return dict(
        cache_enabled=body.cache_enabled,
        scope="current_session",
        note="Search preference is scoped to this refresh family.",
    )


@router.get("/demo/performance")
def performance(user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        indexes = many(
            conn, "SELECT indexname AS name,indexdef AS definition FROM pg_indexes WHERE tablename='students'"
        )
    path = ROOT / "docs/benchmark-results.json"
    return dict(
        indexes=indexes,
        before_explain=None,
        after_explain=None,
        benchmark=json.loads(path.read_text()) if path.exists() else None,
        cache_semantics="Application cold bypasses result cache only; database buffers remain warm.",
    )


@router.post("/demo/benchmarks", status_code=202)
def web_benchmark(body: BenchmarkRequest, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)):
    allow(user, "ADMIN", "OFFICER")
    if not settings.demo_mode or not settings.local_benchmark_enabled or not settings.demo_controls_enabled:
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
            conn.execute("SELECT pg_advisory_xact_lock(26263,77)")
            if one(
                conn, "SELECT 1 FROM benchmark_runs WHERE status='RUNNING' AND created_at>now()-interval '5 minutes'"
            ):
                fail("BENCHMARK_RUNNING", 409)
            limit(("benchmark", str(user["id"])), 1, 60)
            run = uuid4()
            conn.execute(
                "INSERT INTO benchmark_runs(id,requested_by,status) VALUES (%s,%s,'RUNNING')", (run, user["id"])
            )
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
                measured.update(
                    samples_count=body.runs,
                    measured_at=str(datetime.now(timezone.utc)),
                )
                conn.execute(
                    "UPDATE benchmark_runs SET status='COMPLETED',result=%s,finished_at=now() WHERE id=%s",
                    (Jsonb(measured), run_id),
                )
        except Exception:
            with connect() as conn:
                conn.execute(
                    "UPDATE benchmark_runs SET status='FAILED',result=%s,finished_at=now() WHERE id=%s",
                    (Jsonb({"error": "BENCHMARK_FAILED"}), run_id),
                )

    if created:
        tasks.add_task(execute_benchmark, result["run_id"])
    return result


@router.get("/demo/benchmarks/{run_id}")
def benchmark_result(run_id: UUID, user=Depends(authenticated)):
    allow(user, "ADMIN", "OFFICER")
    if not settings.demo_mode or not settings.local_benchmark_enabled or not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    from app.core.lifecycle import local_connection

    try:
        local_connection(settings.database_url)
    except RuntimeError:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        row = one(
            conn,
            "SELECT id AS run_id,status,result,created_at,finished_at,requested_by FROM benchmark_runs WHERE id=%s",
            (run_id,),
        )
        if not row:
            fail("NOT_FOUND", 404)
        if user["role_code"] == "OFFICER" and row["requested_by"] != user["id"]:
            fail("NOT_FOUND", 404)
        row.pop("requested_by")
        return {**row, **(row.get("result") or {})}

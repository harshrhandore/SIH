import csv
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from io import StringIO
from time import perf_counter
from uuid import UUID, uuid4
import jwt
from fastapi import FastAPI, APIRouter, Request, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ConfigDict
from psycopg.types.json import Jsonb
from app.settings import settings, ROOT
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import (
    authenticated,
    allow,
    scope_ids,
    institution_scope,
    student_scope,
    public_user,
    password_ok,
    issue,
    hash_token,
    reason,
)
from app.core.rate_limit import limit
from app.core.cache import cache
from app.core.files import store, read, contained, root_path
from app.core.algorithms import normalized_name, valid_id, career, CATALOGUE
from app.core.audit import append, verify
from app.modules.students.service import passport, trust_for, evidenced_skills, dashboard, epoch, jsonable
from app.modules.imports import service as imports
from app.modules.certificates import service as certificates


@asynccontextmanager
async def lifespan(app):
    with connect() as conn:
        conn.execute(
            "UPDATE import_jobs SET status='FAILED',error_code='PROCESS_INTERRUPTED',error_message='Process restarted; retry from checkpoint.' WHERE status='RUNNING' AND heartbeat_at<now()-interval '60 seconds'"
        )
    yield


app = FastAPI(title="Shiksham APAAR synthetic academic ledger", version="1.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1")


@app.middleware("http")
async def transport(request, call_next):
    request.state.request_id = "req_" + uuid4().hex[:16]
    request.state.started = perf_counter()
    origin = request.headers.get("origin")
    if origin and origin != settings.web_origin:
        return JSONResponse(
            {
                "error": dict(
                    code="ORIGIN_FORBIDDEN",
                    message="Origin is not permitted.",
                    fields=[],
                    request_id=request.state.request_id,
                )
            },
            status_code=403,
        )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if response.status_code == 429:
        response.headers["Retry-After"] = "60"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    error = (
        exc.detail if isinstance(exc.detail, dict) else dict(code="REQUEST_FAILED", message=str(exc.detail), fields=[])
    )
    return JSONResponse({"error": {**error, "request_id": request.state.request_id}}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "error": dict(
                code="VALIDATION_ERROR",
                message="Request fields are invalid.",
                fields=[
                    dict(field=".".join(str(v) for v in e["loc"]), code=e["type"], message=e["msg"])
                    for e in exc.errors()
                ],
                request_id=request.state.request_id,
            )
        },
        status_code=422,
    )


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Strict):
    email: str = Field(max_length=254)
    password: str = Field(max_length=72)


class Refresh(Strict):
    refresh_token: str


class Logout(Strict):
    all_sessions: bool = False


class Mapping(Strict):
    mapping: dict[str, str]
    date_format: str = "DD/MM/YYYY"


class Confirm(Strict):
    confirm_synthetic_data: bool


class Reason(Strict):
    reason: str = Field(min_length=10, max_length=1000)


class Decision(Reason):
    expected_version: int = Field(ge=1)
    action: str
    requested_fields: list[str] = []


class Patch(Reason):
    expected_version: int = Field(ge=1)
    patch: dict


class Career(Strict):
    question: str = Field(min_length=1, max_length=1000)
    role_code: str | None = None


class Version(Strict):
    expected_version: int = Field(ge=1)


class VerifyAlias(Strict):
    certificate_id: UUID


class CandidateDecision(Reason):
    action: str
    case_id: UUID
    expected_case_version: int = Field(ge=1)


class SessionControls(Strict):
    cache_enabled: bool


def listing(items, total=None, page=1, page_size=25, **extra):
    return dict(items=items, total=len(items) if total is None else total, page=page, page_size=page_size, **extra)


def pagination(page, size):
    if page < 1 or size not in {25, 50}:
        fail("INVALID_PAGINATION")
    if (page - 1) * size > 10000:
        fail("OFFSET_LIMIT")
    return (page - 1) * size


def batch_scope(conn, user, batch_id):
    allow(user, "OPERATOR", "OFFICER")
    batch = one(conn, "SELECT * FROM import_batches WHERE id=%s", (batch_id,))
    if not batch or batch["institution_id"] not in scope_ids(user):
        fail("NOT_FOUND", 404)
    return batch


def idem(conn, user, request, body, work):
    raw = request.headers.get("idempotency-key")
    try:
        key = UUID(raw or "")
    except ValueError:
        fail("IDEMPOTENCY_KEY_REQUIRED")
    digest = hashlib.sha256(json.dumps(jsonable(body), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(user["id"]) + str(key),))
    old = one(conn, "SELECT * FROM api_idempotency WHERE actor_id=%s AND key=%s", (user["id"], key))
    operation = request.method + " " + request.url.path
    if old:
        if old["request_hash"] != digest or old["operation"] != operation:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return old["response_body"]
    result = jsonable(work(key))
    conn.execute(
        "INSERT INTO api_idempotency(actor_id,key,operation,request_hash,response_status,response_body) VALUES (%s,%s,%s,%s,200,%s)",
        (user["id"], key, operation, digest, Jsonb(result)),
    )
    return result


@router.get("/health/live")
def live():
    return dict(status="ok", service="shiksham-api")


@router.get("/health/ready")
def ready():
    try:
        with connect() as conn:
            state = one(conn, "SELECT seed_ready FROM app_state")
            migration = one(conn, "SELECT version_num FROM alembic_version")
        if state["seed_ready"] and migration["version_num"] == "0003_views":
            import shutil

            return dict(
                status="ready",
                database=True,
                migrations=True,
                seed_ready=True,
                ocr="tesseract" if shutil.which("tesseract") else "pdf_text_only",
            )
    except Exception:
        pass
    fail("NOT_READY", 503, "Database is waking up or bootstrap is incomplete.")


@router.get("/auth/demo-accounts")
def accounts():
    if not settings.demo_mode:
        fail("NOT_FOUND", 404)
    return dict(
        accounts=[
            dict(key=k, email=e, label=label, role=r)
            for k, e, label, r in [
                ("operator_a", "operator.a@example.test", "College Operator — Institution A", "OPERATOR"),
                ("operator_b", "operator.b@example.test", "College Operator — Institution B", "OPERATOR"),
                ("officer", "officer@example.test", "Verification Officer", "OFFICER"),
                ("admin", "admin@example.test", "AICTE Administrator", "ADMIN"),
                ("student", "student.riya@example.test", "Student — Riya Sharma", "STUDENT"),
            ]
        ],
        password_required=True,
    )


@router.post("/auth/login")
def login(body: Login, request: Request):
    limit(("login", body.email.casefold(), request.client.host if request.client else "unknown"))
    with connect() as conn:
        user = one(conn, "SELECT * FROM users WHERE lower(email)=%s AND active", (body.email.strip().casefold(),))
        if not user or not password_ok(body.password, user["password_hash"]):
            fail("INVALID_CREDENTIALS", 401, "Email or password is invalid.")
        return issue(conn, user)


@router.post("/auth/refresh")
def refresh(body: Refresh, request: Request):
    reused = False
    with connect() as conn:
        session = one(
            conn, "SELECT * FROM refresh_sessions WHERE token_hash=%s FOR UPDATE", (hash_token(body.refresh_token),)
        )
        if not session or session["expires_at"] < datetime.now(timezone.utc):
            fail("REFRESH_EXPIRED", 401)
        if session["rotated_at"] or session["revoked_at"]:
            conn.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE family_id=%s", (session["family_id"],))
            reused = True
        elif hash_token(request.headers.get("x-csrf-token", "")) != session["csrf_hash"]:
            fail("CSRF_INVALID", 403)
        else:
            conn.execute("UPDATE refresh_sessions SET rotated_at=now() WHERE id=%s", (session["id"],))
            user = one(conn, "SELECT * FROM users WHERE id=%s AND active", (session["user_id"],))
            if not user:
                fail("REFRESH_EXPIRED", 401)
            result = issue(conn, user, session["family_id"])
    if reused:
        fail("REFRESH_REUSED", 401)
    return result


@router.post("/auth/logout")
def logout(body: Logout, user=Depends(authenticated)):
    with connect() as conn:
        if body.all_sessions:
            conn.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE user_id=%s", (user["id"],))
        else:
            conn.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE family_id=%s", (user["sid"],))
    return dict(logged_out=True)


@router.get("/auth/me")
def me(user=Depends(authenticated)):
    with connect() as conn:
        return public_user(conn, user)


@router.get("/institutions")
def institutions(state: str | None = None, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    ids = institution_scope(user, admin=True)
    with connect() as conn:
        rows = many(
            conn,
            "SELECT id,name,state,aicte_code FROM institutions WHERE (%s::uuid[] IS NULL OR id=ANY(%s::uuid[])) AND (%s::text IS NULL OR state=%s) ORDER BY name",
            (ids, ids, state, state),
        )
        return listing(rows)


@router.get("/institutions/{institution_id}/programs")
def programs(institution_id: UUID, user=Depends(authenticated)):
    institution_scope(user, institution_id, admin=True)
    with connect() as conn:
        return listing(many(conn, "SELECT * FROM programs WHERE institution_id=%s ORDER BY name", (institution_id,)))


@router.get("/dashboard")
def get_dashboard(institution_id: UUID | None = None, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER")
    ids = institution_scope(user, institution_id)
    if not institution_id and user["role_code"] == "OFFICER":
        fail("INSTITUTION_REQUIRED")
    with connect() as conn:
        return dashboard(conn, ids[0])


@router.get("/students/search")
def search(
    request: Request,
    q: str = "",
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    branch: str | None = None,
    current_year: int | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "name",
    user=Depends(authenticated),
):
    allow(user, "OPERATOR", "OFFICER")
    offset = pagination(page, page_size)
    ids = institution_scope(user, institution_id)
    if len(q) > 100 or q and len(q.strip()) < 2:
        fail("QUERY_TOO_SHORT")
    if sort not in {"name", "admission_year"}:
        fail("UNKNOWN_SORT")
    q = q.strip()
    branch = branch or None
    with connect() as conn:
        data_epoch = one(
            conn,
            "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs WHERE institution_id=ANY(%s::uuid[])",
            (ids,),
        )["e"]
        key = (
            str(user["id"]),
            user["role_code"],
            tuple(str(i) for i in ids),
            data_epoch,
            q,
            branch,
            current_year,
            str(program_id),
            page,
            page_size,
            sort,
        )
        result = (
            None
            if settings.demo_controls_enabled
            and (
                request.headers.get("x-demo-cache") == "bypass"
                or cache.get(("session-controls", str(user["sid"]))) is False
            )
            else cache.get(key)
        )
        hit = bool(result)
        if result is None:
            escaped = normalized_name(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            predicate = "s.institution_id=ANY(%s::uuid[]) AND (%s='' OR s.normalized_name LIKE %s OR s.apaar_id=%s OR s.submitted_enrollment_no=%s) AND (%s::uuid IS NULL OR s.program_id=%s) AND (%s::text IS NULL OR p.branch=%s) AND (%s::int IS NULL OR s.current_year=%s)"
            params = (
                ids,
                q,
                "%" + escaped + "%",
                q.upper(),
                q.upper(),
                program_id,
                program_id,
                branch,
                branch,
                current_year,
                current_year,
            )
            total = one(
                conn,
                "SELECT count(*)::int AS n FROM students s LEFT JOIN programs p ON p.id=s.program_id WHERE "
                + predicate,
                params,
            )["n"]
            order = "s.normalized_name ASC,s.id ASC" if sort == "name" else "s.admission_year DESC,s.id ASC"
            rows = many(
                conn,
                "SELECT s.id,s.full_name,s.apaar_id,s.institution_id,p.name AS program,p.branch,s.current_year,s.data_quality_status,s.external_status,s.version_no FROM students s LEFT JOIN programs p ON p.id=s.program_id WHERE "
                + predicate
                + " ORDER BY "
                + order
                + " LIMIT %s OFFSET %s",
                params + (page_size, offset),
            )
            result = jsonable(listing(rows, total, page, page_size, data_epoch=data_epoch))
            cache.put(key, result)
    return {
        **result,
        "cache": "HIT" if hit else "MISS",
        "took_ms": round((perf_counter() - request.state.started) * 1000, 3),
    }


@router.get("/students/{student_id}")
def student(student_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        return passport(conn, student_scope(conn, user, student_id, request))


@router.get("/student/{apaar_id}")
def student_by_id(apaar_id: str, request: Request, user=Depends(authenticated)):
    if not valid_id(apaar_id):
        fail("INVALID_SYNTHETIC_ID")
    with connect() as conn:
        row = one(conn, "SELECT id FROM students WHERE apaar_id=%s", (apaar_id,))
        if not row:
            fail("NOT_FOUND", 404)
        return passport(conn, student_scope(conn, user, row["id"], request))


@router.get("/students/{student_id}/trust")
def student_trust(student_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        return trust_for(conn, student_scope(conn, user, student_id, request))


@router.get("/students/{student_id}/versions")
def versions(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    offset = pagination(page, page_size)
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        rows = many(
            conn,
            "SELECT version_no,changed_fields,reason,created_at,changed_by FROM record_versions WHERE student_id=%s ORDER BY version_no DESC LIMIT %s OFFSET %s",
            (student_id, page_size, offset),
        )
        return listing(
            rows,
            one(conn, "SELECT count(*) AS n FROM record_versions WHERE student_id=%s", (student_id,))["n"],
            page,
            page_size,
        )


@router.patch("/students/{student_id}")
def patch_student(student_id: UUID, body: Patch, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR")
    reason(body.reason)
    from app.modules.students.corrections import correct

    with connect() as conn:
        student_scope(conn, user, student_id, request)
        return idem(conn, user, request, body.model_dump(), lambda key: correct(conn, user, student_id, body))


@router.post("/imports", status_code=201)
def upload_import(
    request: Request, file: UploadFile = File(...), institution_id: UUID = Form(...), user=Depends(authenticated)
):
    allow(user, "OPERATOR")
    institution_scope(user, institution_id)
    data = file.file.read(20 * 1024 * 1024 + 1)
    with connect() as conn:
        return idem(
            conn,
            user,
            request,
            dict(sha=hashlib.sha256(data).hexdigest(), institution=str(institution_id)),
            lambda key: imports.upload(conn, user, data, file.filename or "", key),
        )


@router.get("/imports")
def list_imports(page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    offset = pagination(page, page_size)
    ids = institution_scope(user, admin=True)
    with connect() as conn:
        cols = (
            "id,institution_id,status,total_rows,processed_rows,clean_rows,flagged_rows,incomplete_rows,created_at"
            + ("" if user["role_code"] == "ADMIN" else ",filename")
        )
        rows = many(
            conn,
            f"SELECT {cols} FROM import_batches WHERE (%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[])) ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (ids, ids, page_size, offset),
        )
        total = one(
            conn,
            "SELECT count(*) AS n FROM import_batches WHERE (%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[]))",
            (ids, ids),
        )["n"]
        return listing(rows, total, page, page_size)


@router.get("/imports/{batch_id}")
def import_detail(batch_id: UUID, user=Depends(authenticated)):
    with connect() as conn:
        batch = batch_scope(conn, user, batch_id)
        rows = many(
            conn,
            "SELECT row_no,raw_data,normalized_data,status FROM import_rows WHERE batch_id=%s ORDER BY row_no LIMIT 20",
            (batch_id,),
        )
        job = one(conn, "SELECT * FROM import_jobs WHERE batch_id=%s", (batch_id,))
        return {
            **{k: batch[k] for k in ["id", "filename", "status", "total_rows", "processed_rows", "column_mapping"]},
            "preview": rows,
            "report": imports.report(conn, batch_id),
            "job": job,
        }


@router.put("/imports/{batch_id}/mapping")
def set_mapping(batch_id: UUID, body: Mapping, user=Depends(authenticated)):
    allow(user, "OPERATOR")
    with connect() as conn:
        batch = batch_scope(conn, user, batch_id)
        if batch["status"] not in {"UPLOADED", "MAPPED"}:
            fail("IMPORT_ALREADY_STARTED", 409)
        rows = many(
            conn, "SELECT row_no,raw_data FROM import_rows WHERE batch_id=%s ORDER BY row_no LIMIT 20", (batch_id,)
        )
        headers = set(rows[0]["raw_data"])
        if set(body.mapping.values()) - headers or set(body.mapping) - set(imports.ALIASES):
            fail("UNKNOWN_COLUMN", 400)
        if len(set(body.mapping.values())) != len(body.mapping):
            fail("DUPLICATE_MAPPING", 400)
        if imports.MANDATORY - set(body.mapping):
            fail("REQUIRED_MAPPING_MISSING")
        if body.date_format not in {"DD/MM/YYYY", "ISO"}:
            fail("DATE_FORMAT_UNSUPPORTED")
        conn.execute(
            "UPDATE import_batches SET status='MAPPED',column_mapping=%s WHERE id=%s",
            (Jsonb(body.model_dump()), batch_id),
        )
        return dict(
            batch_id=batch_id,
            status="MAPPED",
            required_fields_mapped=True,
            preview=[
                dict(
                    row_no=r["row_no"],
                    normalized=imports.normalized(r["raw_data"], body.mapping, body.date_format),
                    errors=[],
                )
                for r in rows
            ],
        )


@router.post("/imports/{batch_id}/validate", status_code=202)
def validate_import(
    batch_id: UUID, body: Confirm, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)
):
    allow(user, "OPERATOR")
    if not body.confirm_synthetic_data:
        fail("SYNTHETIC_CONFIRMATION_REQUIRED")
    with connect() as conn:
        batch = batch_scope(conn, user, batch_id)

        def work(key):
            if batch["status"] != "MAPPED":
                fail("MAPPING_REQUIRED", 409)
            job = imports.start(conn, batch)
            return dict(job_id=job, batch_id=batch_id, status="QUEUED", poll_url=f"/api/v1/import-jobs/{job}")

        result = idem(conn, user, request, body.model_dump(), work)
    tasks.add_task(imports.process, result["job_id"])
    return result


@router.get("/import-jobs/{job_id}")
def get_job(job_id: UUID, user=Depends(authenticated)):
    with connect() as conn:
        job = one(conn, "SELECT * FROM import_jobs WHERE id=%s", (job_id,))
        if not job:
            fail("NOT_FOUND", 404)
        batch = batch_scope(conn, user, job["batch_id"])
        return {**job, "processed_rows": batch["processed_rows"], "total_rows": batch["total_rows"]}


@router.post("/import-jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: UUID, body: Reason, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)):
    allow(user, "OPERATOR")
    with connect() as conn:
        job = one(conn, "SELECT * FROM import_jobs WHERE id=%s FOR UPDATE", (job_id,))
        if not job:
            fail("NOT_FOUND", 404)
        batch_scope(conn, user, job["batch_id"])
        if job["status"] != "FAILED" or job["retry_count"] >= 3:
            fail("RETRY_NOT_ALLOWED", 409)
        conn.execute(
            "UPDATE import_jobs SET status='QUEUED',retry_count=retry_count+1,error_code=NULL,error_message=NULL WHERE id=%s",
            (job_id,),
        )
    tasks.add_task(imports.process, job_id)
    return dict(job_id=job_id, status="QUEUED")


@router.get("/imports/{batch_id}/report")
def import_report(batch_id: UUID, user=Depends(authenticated)):
    with connect() as conn:
        batch_scope(conn, user, batch_id)
        return imports.report(conn, batch_id)


@router.get("/imports/{batch_id}/errors.csv")
def errors_csv(batch_id: UUID, user=Depends(authenticated)):
    with connect() as conn:
        batch_scope(conn, user, batch_id)
        rows = many(
            conn,
            "SELECT row_no,field,code,is_primary,message,evidence FROM import_errors WHERE batch_id=%s ORDER BY row_no,id",
            (batch_id,),
        )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_no", "field", "code", "is_primary", "message", "submitted_value", "expected"])

    def safe(value):
        value = str(value or "")
        return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value

    for row in rows:
        writer.writerow(
            [safe(row[k]) for k in ["row_no", "field", "code", "is_primary", "message"]]
            + [safe(row["evidence"].get(k)) for k in ["submitted_value", "expected"]]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="import-errors.csv"'},
    )


def masked(row):
    name = row.get("full_name") or ""
    identifier = row.get("submitted_apaar_id") or ""
    ref = hmac.new(settings.mask_secret.encode(), str(row["student_id"]).encode(), hashlib.sha256).hexdigest()[:12]
    return dict(
        case_id=row["id"],
        id=row["id"],
        student_ref=ref,
        masked_name=name[:2] + "****" + name[-2:],
        masked_apaar_id="SYN-***********" + identifier[-2:],
        institution_name=row.get("institution_name"),
        status=row["status"],
        opened_reason=row["opened_reason"],
        version_no=row["version_no"],
    )


@router.get("/cases")
def list_cases(
    status: str | None = None,
    institution_id: UUID | None = None,
    rule: str | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    offset = pagination(page, page_size)
    ids = institution_scope(user, institution_id, admin=True)
    if user["role_code"] == "ADMIN" and q:
        fail("RAW_PII_SEARCH_FORBIDDEN")
    if status and status not in {"OPEN", "CORRECTION_REQUESTED", "ESCALATED", "APPROVED"}:
        fail("INVALID_STATUS")
    with connect() as conn:
        pred = "(%s::uuid[] IS NULL OR s.institution_id=ANY(%s::uuid[])) AND (%s::text IS NULL OR c.status=%s) AND (%s::text IS NULL OR c.opened_reason=%s) AND (%s='' OR s.normalized_name LIKE %s OR s.submitted_enrollment_no=%s)"
        params = (ids, ids, status, status, rule, rule, q, "%" + normalized_name(q) + "%", q.upper())
        rows = many(
            conn,
            "SELECT c.*,s.full_name,s.submitted_apaar_id,s.submitted_enrollment_no,s.institution_id,i.name AS institution_name FROM review_cases c JOIN students s ON s.id=c.student_id JOIN institutions i ON i.id=s.institution_id WHERE "
            + pred
            + " ORDER BY c.created_at,c.id LIMIT %s OFFSET %s",
            params + (page_size, offset),
        )
        total = one(
            conn, "SELECT count(*) AS n FROM review_cases c JOIN students s ON s.id=c.student_id WHERE " + pred, params
        )["n"]
        return listing([masked(r) for r in rows] if user["role_code"] == "ADMIN" else rows, total, page, page_size)


@router.get("/cases/{case_id}")
def case_detail(case_id: UUID, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    with connect() as conn:
        row = one(
            conn,
            "SELECT c.*,s.institution_id,s.full_name,s.submitted_apaar_id,i.name AS institution_name FROM review_cases c JOIN students s ON s.id=c.student_id JOIN institutions i ON i.id=s.institution_id WHERE c.id=%s",
            (case_id,),
        )
        if not row:
            fail("NOT_FOUND", 404)
        if user["role_code"] == "ADMIN" and not request.headers.get("x-case-access"):
            return dict(
                case=masked(row),
                masked=True,
                allowed_actions=["ACCESS_ESCALATED"] if row["status"] == "ESCALATED" else [],
            )
        student = student_scope(conn, user, row["student_id"], request)
        findings = many(
            conn,
            "SELECT check_code AS code,severity,explanation,evidence FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
            (student["id"],),
        )
        # Do not expose related other-student data in scoped case responses.
        duplicates = many(
            conn,
            "SELECT id,match_type,score,status FROM duplicate_candidates WHERE (student_a=%s OR student_b=%s) AND status='OPEN'",
            (student["id"], student["id"]),
        )
        actions = []
        if user["role_code"] in {"OFFICER", "ADMIN"} and row["status"] != "APPROVED":
            actions = ["REQUEST_CORRECTION", "ESCALATE"]
            if not findings and not duplicates:
                actions.append("APPROVE")
        return dict(
            case={k: row[k] for k in ["id", "student_id", "status", "opened_reason", "version_no"]},
            student=passport(conn, student),
            findings=findings,
            comparison=[],
            duplicates=duplicates,
            versions=many(
                conn,
                "SELECT version_no,changed_fields,reason,created_at FROM record_versions WHERE student_id=%s ORDER BY version_no",
                (student["id"],),
            ),
            decisions=many(
                conn,
                "SELECT action,reason,created_at FROM review_decisions WHERE case_id=%s ORDER BY created_at",
                (case_id,),
            ),
            allowed_actions=actions,
        )


@router.post("/cases/{case_id}/access")
def case_access(case_id: UUID, body: Reason, user=Depends(authenticated)):
    allow(user, "ADMIN")
    reason(body.reason)
    with connect() as conn:
        case = one(
            conn,
            "SELECT c.*,s.institution_id FROM review_cases c JOIN students s ON s.id=c.student_id WHERE c.id=%s FOR UPDATE OF c",
            (case_id,),
        )
        if not case:
            fail("NOT_FOUND", 404)
        if case["status"] != "ESCALATED":
            fail("CASE_NOT_ESCALATED", 409)
        conn.execute(
            "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,'ACCESS_ESCALATED',%s,%s)",
            (case_id, user["id"], body.reason, case["version_no"]),
        )
        append(
            conn,
            case["institution_id"],
            user["id"],
            "ACCESS_ESCALATED",
            "case",
            case_id,
            body.reason,
            {},
            case["student_id"],
        )
        token = jwt.encode(
            dict(
                sub=str(user["id"]),
                case_id=str(case_id),
                student_id=str(case["student_id"]),
                version=case["version_no"],
                exp=datetime.now(timezone.utc) + timedelta(minutes=5),
                aud="case-access",
            ),
            settings.grant_secret,
            algorithm="HS256",
        )
        return dict(access_grant=token, expires_in=300, case_id=case_id, scope="case_only")


@router.post("/cases/{case_id}/decisions")
def decide(case_id: UUID, body: Decision, request: Request, user=Depends(authenticated)):
    allow(user, "OFFICER", "ADMIN")
    reason(body.reason)
    with connect() as conn:

        def work(key):
            case = one(conn, "SELECT * FROM review_cases WHERE id=%s FOR UPDATE", (case_id,))
            if not case:
                fail("NOT_FOUND", 404)
            student = student_scope(conn, user, case["student_id"], request)
            if case["version_no"] != body.expected_version:
                fail("VERSION_CONFLICT", 409)
            target = {"REQUEST_CORRECTION": "CORRECTION_REQUESTED", "ESCALATE": "ESCALATED", "APPROVE": "APPROVED"}.get(
                body.action
            )
            if (
                not target
                or case["status"] not in {"OPEN", "ESCALATED"}
                or case["status"] == "ESCALATED"
                and target == "ESCALATED"
            ):
                fail("INVALID_TRANSITION", 409)
            if body.action == "REQUEST_CORRECTION" and not body.requested_fields:
                fail("REQUESTED_FIELDS_REQUIRED")
            if body.action == "APPROVE":
                if one(
                    conn,
                    "SELECT 1 FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL LIMIT 1",
                    (student["id"],),
                ) or one(
                    conn,
                    "SELECT 1 FROM duplicate_candidates WHERE (student_a=%s OR student_b=%s) AND status='OPEN' LIMIT 1",
                    (student["id"], student["id"]),
                ):
                    fail("UNRESOLVED_FINDINGS", 409)
            updated = one(
                conn,
                "UPDATE review_cases SET status=%s,version_no=version_no+1,updated_at=now(),escalated_at=CASE WHEN %s='ESCALATED' THEN now() ELSE escalated_at END WHERE id=%s RETURNING *",
                (target, target, case_id),
            )
            decision = one(
                conn,
                "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (case_id, user["id"], body.action, body.reason, updated["version_no"]),
            )
            append(
                conn,
                student["institution_id"],
                user["id"],
                "REVIEW_APPROVED" if target == "APPROVED" else body.action,
                "case",
                case_id,
                body.reason,
                dict(requested_fields=body.requested_fields, student_version=student["version_no"]),
                student["id"],
            )
            trust_for(conn, student)
            return dict(case=updated, decision_id=decision["id"], data_epoch=epoch(conn, student["institution_id"]))

        return idem(conn, user, request, body.model_dump(), work)


@router.get("/students/{student_id}/timeline")
def timeline(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    offset = pagination(page, page_size)
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)
        conn.commit()
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        checked = verify(conn, student["institution_id"])
        rows = many(
            conn,
            "SELECT e.id AS event_id,e.action,e.occurred_at,e.reason,e.payload,e.sequence_no,e.row_hash,u.full_name AS actor_name FROM audit_events e JOIN users u ON u.id=e.actor_id WHERE student_id=%s ORDER BY sequence_no DESC LIMIT %s OFFSET %s",
            (student_id, page_size, offset),
        )
        for row in rows:
            row["hash_verified"] = checked["valid"]
            row["changes"] = row.pop("payload").get("changes", {})
        return listing(
            rows,
            one(conn, "SELECT count(*) AS n FROM audit_events WHERE student_id=%s", (student_id,))["n"],
            page,
            page_size,
            chain_verified_at=checked["checked_at"],
            checked_head_seq=checked.get("head_seq"),
            verified=checked["valid"],
        )


@router.get("/audit/verify-chain")
def verify_chain(institution_id: UUID, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    institution_scope(user, institution_id, admin=True)
    with connect() as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return verify(conn, institution_id)


@router.post("/students/{student_id}/certificates", status_code=201)
def upload_certificate(
    student_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("TRIAL"),
    title: str = Form("Synthetic certificate"),
    user=Depends(authenticated),
):
    allow(user, "OPERATOR", "OFFICER", "STUDENT")
    if purpose not in {"PASSPORT", "TRIAL"}:
        fail("INVALID_PURPOSE")
    data = file.file.read(10 * 1024 * 1024 + 1)
    mime, suffix = certificates.inspect_document(data)
    sha = hashlib.sha256(data).hexdigest()
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)

        def work(key):
            existing = one(
                conn,
                "SELECT id FROM certificates WHERE student_id=%s AND file_sha256=%s AND purpose=%s",
                (student_id, sha, purpose),
            )
            if existing:
                return dict(
                    certificate_id=existing["id"],
                    purpose=purpose,
                    file_sha256=sha,
                    status="PENDING",
                    duplicate_of=existing["id"],
                )
            storage, _ = store(data, student["institution_id"], student_id, suffix)
            cid = uuid4()
            conn.execute(
                "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, student_id, title, storage, sha, mime, purpose, user["id"]),
            )
            append(
                conn,
                student["institution_id"],
                user["id"],
                "CERTIFICATE_UPLOADED",
                "certificate",
                cid,
                "Uploaded synthetic certificate for local checks.",
                dict(purpose=purpose),
                student_id,
            )
            epoch(conn, student["institution_id"])
            return dict(certificate_id=cid, purpose=purpose, file_sha256=sha, status="PENDING", duplicate_of=None)

        return idem(conn, user, request, dict(sha=sha, purpose=purpose, title=title), work)


@router.post("/certificates/{certificate_id}/verify")
def verify_certificate(certificate_id: UUID, request: Request, user=Depends(authenticated)):
    from app.core.verification_lock import verification_slot

    with verification_slot():
        return verify_certificate_locked(certificate_id, request, user)


def verify_certificate_locked(certificate_id, request, user):
    allow(user, "OPERATOR", "OFFICER", "STUDENT")
    limit(("certificate", str(user["id"])), 20)
    try:
        key = UUID(request.headers.get("idempotency-key", ""))
    except ValueError:
        fail("IDEMPOTENCY_KEY_REQUIRED")
    with connect() as conn:
        certificate = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        if not certificate:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, certificate["student_id"], request)
        old = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s",
            (certificate_id, key),
        )
        if old:
            return report_response(old, certificate)
        if certificate["processing_status"] == "PROCESSING" and certificate["processing_started_at"] > datetime.now(
            timezone.utc
        ) - timedelta(seconds=120):
            fail("VERIFICATION_RUNNING", 409)
        conn.execute(
            "UPDATE certificates SET processing_status='PROCESSING',processing_started_at=now() WHERE id=%s",
            (certificate_id,),
        )
        data = read(certificate["storage_key"]).read_bytes()
        reuse = []
        if one(
            conn,
            "SELECT 1 FROM certificates WHERE file_sha256=%s AND student_id<>%s LIMIT 1",
            (certificate["file_sha256"], student["id"]),
        ):
            reuse.append(("SHA_REUSE_OTHER_STUDENT", 60))
    result = certificates.evaluate(data, certificate["mime_type"], student, reuse)
    with connect() as conn:
        student_scope(conn, user, student["id"], request)
        extracted = result["extracted"]
        if (
            extracted["issuer"]
            and extracted["credential_id"]
            and one(
                conn,
                "SELECT 1 FROM certificates WHERE lower(issuer)=lower(%s) AND lower(credential_id)=lower(%s) AND student_id<>%s LIMIT 1",
                (extracted["issuer"], extracted["credential_id"], student["id"]),
            )
        ):
            result = certificates.evaluate(
                data, certificate["mime_type"], student, reuse + [("CREDENTIAL_REUSE_OTHER_STUDENT", 65)]
            )
        current = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        prior = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s",
            (certificate_id, key),
        )
        if prior:
            return report_response(prior, current)
        fresh = student_scope(conn, user, student["id"], request)
        if fresh["version_no"] != student["version_no"]:
            conn.execute("UPDATE certificates SET processing_status='FAILED' WHERE id=%s", (certificate_id,))
            fail("VERSION_CONFLICT", 409)
        response = certificates.persist_report(conn, certificate, student, result, key, user["id"])
        trust_for(conn, student)
        epoch(conn, student["institution_id"])
        return response


def report_response(row, certificate):
    return {
        **row["reasons"],
        "verification_id": row["id"],
        "certificate_id": certificate["id"],
        "purpose": certificate["purpose"],
        "trust_effect": "EXCLUDED_TRIAL" if certificate["purpose"] == "TRIAL" else "PASSPORT_EVIDENCE",
        "created_at": row["created_at"],
    }


@router.get("/certificate-verifications/{verification_id}")
def report(verification_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        row = one(conn, "SELECT * FROM certificate_verifications WHERE id=%s", (verification_id,))
        if not row:
            fail("NOT_FOUND", 404)
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s", (row["certificate_id"],))
        student_scope(conn, user, cert["student_id"], request)
        return report_response(row, cert)


@router.get("/certificate-verifications/{verification_id}/fraud")
def fraud(verification_id: UUID, request: Request, user=Depends(authenticated)):
    result = report(verification_id, request, user)
    return dict(
        verification_id=verification_id,
        risk=result["risk"]["level"],
        score=result["risk"]["score"],
        reasons=result["risk"]["reasons"],
        limitations=["Heuristic, not validated on real certificates."],
        not_assessed=result["not_assessed"],
    )


@router.get("/certificates/{certificate_id}/file")
def certificate_file(certificate_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s", (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student_scope(conn, user, cert["student_id"], request)
        return FileResponse(
            read(cert["storage_key"]),
            media_type=cert["mime_type"],
            filename="synthetic-certificate." + cert["storage_key"].split(".")[-1],
        )


class Acceptance(Reason):
    action: str


@router.post("/certificates/{certificate_id}/acceptance")
def acceptance(certificate_id: UUID, body: Acceptance, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER")
    reason(body.reason)
    with connect() as conn:
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, cert["student_id"], request)
        if cert["purpose"] == "TRIAL":
            fail("TRIAL_CANNOT_ATTACH", 409)
        latest = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s ORDER BY created_at DESC LIMIT 1",
            (certificate_id,),
        )
        if body.action == "ACCEPT" and (
            not latest or latest["verdict"] != "VERIFIED_LOCAL" or latest["risk_score"] >= 30
        ):
            fail("LOCAL_REPORT_REQUIRED", 409)
        if body.action not in {"ACCEPT", "REJECT"}:
            fail("INVALID_ACTION")
        conn.execute(
            "UPDATE certificates SET acceptance_status=%s,reviewed_at=now(),reviewed_by=%s,resolution_reason=%s WHERE id=%s",
            ("ACCEPTED" if body.action == "ACCEPT" else "REJECTED", user["id"], body.reason, certificate_id),
        )
        append(
            conn,
            student["institution_id"],
            user["id"],
            "CERTIFICATE_REVIEWED",
            "certificate",
            certificate_id,
            body.reason,
            dict(action=body.action),
            student["id"],
        )
        return dict(
            certificate_id=certificate_id,
            acceptance_status="ACCEPTED" if body.action == "ACCEPT" else "REJECTED",
            trust_score=trust_for(conn, student)["score"],
            data_epoch=epoch(conn, student["institution_id"]),
        )


@router.get("/career/roles")
def career_roles(user=Depends(authenticated)):
    allow(user, "STUDENT", "OPERATOR", "OFFICER")
    return dict(
        catalogue_version=1,
        roles=[
            dict(code=k, label=k.replace("_", " ").title(), skills=[dict(code=c, weight=w) for c, w in weights.items()])
            for k, weights in CATALOGUE.items()
        ],
    )


@router.post("/students/{student_id}/career")
def ask_career(student_id: UUID, body: Career, request: Request, user=Depends(authenticated)):
    allow(user, "STUDENT")
    limit(("career", str(user["id"])), 20)
    role = body.role_code
    if not role:
        question = body.question.casefold()
        for k, aliases in {
            "DATA_SCIENTIST": ["data scientist", "data science"],
            "FULL_STACK_DEVELOPER": ["full stack", "full-stack", "web developer"],
            "ML_ENGINEER": ["ml engineer", "machine learning engineer"],
            "CLOUD_ENGINEER": ["cloud engineer"],
        }.items():
            if any(alias in question for alias in aliases):
                role = k
                break
    if role not in CATALOGUE:
        fail("UNKNOWN_CAREER_ROLE", 422, "Choose a supported career role.")
    with connect() as conn:
        student_scope(conn, user, student_id, request)

        def work(key):
            result = career(role, evidenced_skills(conn, student_id))
            sid = uuid4()
            conn.execute(
                "INSERT INTO career_sessions(id,student_id,question,role_code,response,phrasing_source) VALUES (%s,%s,%s,%s,%s,'RULE_BASED')",
                (sid, student_id, body.question, role, Jsonb(result)),
            )
            return {**result, "session_id": sid}

        return idem(conn, user, request, body.model_dump(), work)


@router.get("/students/{student_id}/career/history")
def career_history(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    allow(user, "STUDENT", "OPERATOR", "OFFICER")
    offset = pagination(page, page_size)
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        rows = many(
            conn,
            "SELECT id AS session_id,question,role_code,response,created_at FROM career_sessions WHERE student_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (student_id, page_size, offset),
        )
        return listing(
            rows,
            one(conn, "SELECT count(*) AS n FROM career_sessions WHERE student_id=%s", (student_id,))["n"],
            page,
            page_size,
        )


@router.get("/oversight")
def oversight(
    state: str | None = None,
    institution_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    allow(user, "ADMIN")
    offset = pagination(page, page_size)
    with connect() as conn:
        insts = many(
            conn,
            "SELECT id,name,state FROM institutions WHERE (%s::text IS NULL OR state=%s) AND (%s::uuid IS NULL OR id=%s) ORDER BY name LIMIT %s OFFSET %s",
            (state, state, institution_id, institution_id, page_size, offset),
        )
        rows = []
        for inst in insts:
            data = dashboard(conn, inst["id"])
            rows.append(
                dict(
                    institution_id=inst["id"],
                    institution_name=inst["name"],
                    state=inst["state"],
                    total=data["total"],
                    submission_percent=data["submission_percent"],
                    missing_records=data["missing_records"],
                    unresolved_discrepancies=data["flagged"],
                    pending_reviews=data["pending_reviews"],
                )
            )
        return listing(rows, page=page, page_size=page_size, trend=[])


def analytics_data(kind, user, institution_id, program_id, year, state):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    ids = institution_scope(user, institution_id, admin=True)
    table = {
        "admissions": "mv_admissions",
        "placements": "mv_placements",
        "performance": "mv_performance",
        "data-quality": "mv_data_quality",
    }[kind]
    start = perf_counter()
    with connect() as conn:
        if kind == "data-quality" and (program_id or year):
            fail("PROGRAM_QUALITY_FILTER_NOT_YET_SUPPORTED")
        pred = "(%s::uuid[] IS NULL OR v.institution_id=ANY(%s::uuid[])) AND (%s::text IS NULL OR i.state=%s)"
        params: tuple = (ids, ids, state, state)
        if kind != "data-quality":
            pred += " AND (%s::uuid IS NULL OR v.program_id=%s) AND (%s::int IS NULL OR v.year=%s)"
            params += (program_id, program_id, year, year)
        rows = many(
            conn, f"SELECT v.* FROM {table} v JOIN institutions i ON i.id=v.institution_id WHERE " + pred, params
        )
        refresh = one(conn, "SELECT * FROM analytics_refresh_state WHERE view_name=%s", (table,))
        current = one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs")["e"]
        trend = []
        if kind == "data-quality":
            trend = many(
                conn,
                "SELECT snapshot_date AS date,round(100.0*sum(clean)/nullif(sum(total),0),2) AS clean_percent FROM data_quality_snapshots WHERE (%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[])) GROUP BY snapshot_date ORDER BY snapshot_date",
                (ids, ids),
            )
        return dict(
            items=rows,
            trend=trend,
            took_ms=round((perf_counter() - start) * 1000, 3),
            data_as_of=refresh["refreshed_at"],
            refreshing=refresh["status"] == "RUNNING",
            stale=refresh["source_epoch"] != current,
        )


for kind in ["admissions", "placements", "performance", "data-quality"]:

    def make_endpoint(selected):
        def endpoint(
            institution_id: UUID | None = None,
            program_id: UUID | None = None,
            year: int | None = None,
            state: str | None = None,
            user=Depends(authenticated),
        ):
            return analytics_data(selected, user, institution_id, program_id, year, state)

        endpoint.__name__ = "analytics_" + selected.replace("-", "_")
        return endpoint

    router.add_api_route("/analytics/" + kind, make_endpoint(kind), methods=["GET"])


@router.post("/analytics/refresh", status_code=202)
def refresh_analytics(tasks: BackgroundTasks, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    limit(("refresh", str(user["id"])), 1, 10)

    def refresh():
        with connect() as conn:
            conn.execute("SELECT refresh_demo_views()")

    tasks.add_task(refresh)
    return dict(status="QUEUED", poll_url="/api/v1/analytics/refresh-status")


@router.get("/analytics/refresh-status")
def refresh_status(user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    with connect() as conn:
        views = many(conn, "SELECT view_name AS name,status,refreshed_at,source_epoch FROM analytics_refresh_state")
        current = one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs")["e"]
        return dict(
            status="READY" if all(v["status"] == "READY" for v in views) else "RUNNING",
            views=views,
            stale=any(v["source_epoch"] != current for v in views),
        )


@router.get("/demo/config")
def demo_config(user=Depends(authenticated)):
    if not settings.demo_mode:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        return dict(
            synthetic=True,
            demo_as_of=settings.demo_as_of,
            controls_enabled=settings.demo_controls_enabled,
            cache_enabled_for_session=True,
            llm_enabled=False,
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
    # Runtime has no sandbox privileges. This boundary needs a separate read-only broker.
    fail(
        "SANDBOX_CLI_REQUIRED",
        409,
        "Use python -m app.cli audit-sandbox create or tamper locally; runtime cannot read the owner-only schema.",
    )


@router.post("/verify")
def verify_alias(body: VerifyAlias, request: Request, user=Depends(authenticated)):
    return verify_certificate(body.certificate_id, request, user)


@router.post("/students/{student_id}/checks")
def checks(student_id: UUID, body: Version, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER")
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)
        if student["version_no"] != body.expected_version:
            fail("VERSION_CONFLICT", 409)
        findings = many(
            conn,
            "SELECT check_code AS code,severity,explanation FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
            (student_id,),
        )
        return dict(
            data_quality_status=student["data_quality_status"],
            external_status=student["external_status"],
            findings=findings,
            data_epoch=one(
                conn, "SELECT data_epoch FROM institution_epochs WHERE institution_id=%s", (student["institution_id"],)
            )["data_epoch"],
        )


@router.post("/students/{student_id}/external-check")
def external_check(student_id: UUID, body: Reason, request: Request, user=Depends(authenticated)):
    allow(user, "OFFICER")
    reason(body.reason)
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)
        if student["data_quality_status"] != "PASSED_LOCAL_CHECKS" or not valid_id(student["apaar_id"]):
            fail("LOCAL_CHECKS_REQUIRED", 409)

        def work(key):
            status = "MOCK_NO_MATCH" if int(student["apaar_id"][4:-1]) % 10 == 0 else "MOCK_MATCH"
            evidence = dict(label="MOCK, not official", reasons=["Deterministic synthetic identifier lookup."])
            conn.execute(
                "INSERT INTO external_verifications(student_id,requested_by,adapter,status,evidence) VALUES (%s,%s,'MockApaarAdapter',%s,%s)",
                (student_id, user["id"], status, Jsonb(evidence)),
            )
            conn.execute("UPDATE students SET external_status=%s WHERE id=%s", (status, student_id))
            append(
                conn,
                student["institution_id"],
                user["id"],
                "MOCK_EXTERNAL_CHECK",
                "student",
                student_id,
                body.reason,
                dict(status=status, official=False),
                student_id,
            )
            epoch(conn, student["institution_id"])
            return dict(
                adapter="MockApaarAdapter",
                status=status,
                official=False,
                checked_at=str(datetime.now(timezone.utc)),
                **evidence,
            )

        return idem(conn, user, request, body.model_dump(), work)


@router.post("/duplicate-candidates/{candidate_id}/decision")
def candidate_decision(candidate_id: UUID, body: CandidateDecision, request: Request, user=Depends(authenticated)):
    allow(user, "OFFICER", "ADMIN")
    reason(body.reason)
    if body.action not in {"DISMISS_DUPLICATE", "CONFIRM_DUPLICATE"}:
        fail("INVALID_ACTION")
    with connect() as conn:

        def work(key):
            case = one(conn, "SELECT * FROM review_cases WHERE id=%s FOR UPDATE", (body.case_id,))
            candidate = one(conn, "SELECT * FROM duplicate_candidates WHERE id=%s FOR UPDATE", (candidate_id,))
            if not case or not candidate or case["student_id"] not in {candidate["student_a"], candidate["student_b"]}:
                fail("NOT_FOUND", 404)
            student = student_scope(conn, user, case["student_id"], request)
            if case["version_no"] != body.expected_case_version or candidate["status"] != "OPEN":
                fail("VERSION_CONFLICT", 409)
            status = "DISMISSED" if body.action == "DISMISS_DUPLICATE" else "CONFIRMED"
            conn.execute("UPDATE duplicate_candidates SET status=%s WHERE id=%s", (status, candidate_id))
            conn.execute(
                "UPDATE review_cases SET version_no=version_no+1,updated_at=now() WHERE id=%s", (body.case_id,)
            )
            conn.execute(
                "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,%s,%s,%s)",
                (body.case_id, user["id"], body.action, body.reason, case["version_no"] + 1),
            )
            append(
                conn,
                student["institution_id"],
                user["id"],
                body.action,
                "candidate",
                candidate_id,
                body.reason,
                dict(merged=False),
                student["id"],
            )
            epoch(conn, student["institution_id"])
            return dict(id=candidate_id, status=status, case_version=case["version_no"] + 1, merged=False)

        return idem(conn, user, request, body.model_dump(), work)


@router.get("/audit/events")
def audit_events(
    request: Request,
    institution_id: UUID | None = None,
    case_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    ids = institution_scope(user, institution_id, admin=True)
    offset = pagination(page, page_size)
    with connect() as conn:
        student_id = None
        if case_id:
            case = one(conn, "SELECT * FROM review_cases WHERE id=%s", (case_id,))
            if not case:
                fail("NOT_FOUND", 404)
            if user["role_code"] != "ADMIN" or request.headers.get("x-case-access"):
                student_scope(conn, user, case["student_id"], request)
                student_id = case["student_id"]
            else:
                # An aggregate admin case filter must not become a raw lookup.
                ids = None
                student_id = case["student_id"]
        cols = "id AS event_id,action,occurred_at" + ("" if user["role_code"] == "ADMIN" else ",reason")
        pred = "(%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[])) AND (%s::uuid IS NULL OR student_id=%s)"
        params = (ids, ids, student_id, student_id)
        rows = many(
            conn,
            "SELECT " + cols + " FROM audit_events WHERE " + pred + " ORDER BY occurred_at DESC LIMIT %s OFFSET %s",
            params + (page_size, offset),
        )
        return listing(
            rows, one(conn, "SELECT count(*) AS n FROM audit_events WHERE " + pred, params)["n"], page, page_size
        )


@router.put("/demo/session-controls")
def session_controls(body: SessionControls, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    if not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    # Preference is bound to the active refresh family, never a global switch.
    cache.put(("session-controls", str(user["sid"])), body.cache_enabled)
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


class BenchmarkRequest(Strict):
    dataset: str = "current"
    runs: int = Field(default=20, ge=20, le=100)
    cache_mode: str = "BOTH"


@router.post("/demo/benchmarks", status_code=202)
def web_benchmark(body: BenchmarkRequest, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)):
    allow(user, "ADMIN", "OFFICER")
    if not settings.local_benchmark_enabled or not settings.demo_controls_enabled:
        fail("NOT_FOUND", 404)
    # The command line benchmark owns its synthetic credentials; HTTP never reads local secrets.
    fail("LOCAL_BENCHMARK_CLI_REQUIRED", 409, "Run python scripts/benchmark.py --runs 20 in the local terminal.")


@router.get("/demo/benchmarks/{run_id}")
def benchmark_result(run_id: UUID, user=Depends(authenticated)):
    allow(user, "ADMIN", "OFFICER")
    if not settings.local_benchmark_enabled:
        fail("NOT_FOUND", 404)
    with connect() as conn:
        row = one(
            conn, "SELECT id AS run_id,status,result,created_at,finished_at FROM benchmark_runs WHERE id=%s", (run_id,)
        )
        if not row:
            fail("NOT_FOUND", 404)
        return row


app.include_router(router)

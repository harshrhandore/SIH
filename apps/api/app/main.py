from app.modules.students.router import router as students_router
from app.modules.imports.router import router as imports_router
from app.modules.reviews.router import router as reviews_router
from app.modules.audit.router import router as audit_router
from app.modules.trust.router import router as trust_router
from app.modules.certificates.router import router as certificates_router
from app.modules.career.router import router as career_router
from app.modules.analytics.router import router as analytics_router
from app.modules.verification.router import router as verification_router
from app.modules.demo.router import router as demo_router
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.settings import settings
from app.db.session import connect, one
from app.core.errors import fail
from app.core.logging import log_request
from app.modules.auth.router import router as auth_router
from app.modules.institutions.router import router as institutions_router


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
        log_request(request.state.request_id, 403, perf_counter() - request.state.started)
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
    try:
        response = await call_next(request)
    except Exception:
        log_request(request.state.request_id, 500, perf_counter() - request.state.started)
        raise
    log_request(request.state.request_id, response.status_code, perf_counter() - request.state.started)
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


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "The operation failed. Retry or inspect the protected local server log.",
                "fields": [],
                "request_id": getattr(request.state, "request_id", "unavailable"),
            }
        },
        status_code=500,
    )


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


router.include_router(auth_router)
router.include_router(institutions_router)
router.include_router(students_router)
router.include_router(imports_router)
router.include_router(reviews_router)
router.include_router(audit_router)
router.include_router(trust_router)
router.include_router(certificates_router)
router.include_router(career_router)
router.include_router(analytics_router)
router.include_router(verification_router)
router.include_router(demo_router)
app.include_router(router)

"""Imports HTTP operations."""

from app.core.http import listing, pagination, batch_scope, idem
import csv
import hashlib
from io import StringIO
from uuid import UUID
from fastapi import Request, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response
from psycopg.types.json import Jsonb
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, institution_scope
from app.modules.imports import service as imports
from app.core.contracts import Reason
from app.modules.imports.schemas import Mapping
from app.modules.imports.schemas import Confirm
from fastapi import APIRouter

router = APIRouter(tags=["imports"])


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

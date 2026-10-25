"""Verification HTTP operations."""

from app.core.http import idem
from datetime import datetime, timezone
from uuid import UUID
from fastapi import Request, Depends
from psycopg.types.json import Jsonb
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, student_scope, reason
from app.core.algorithms import valid_id
from app.core.audit import append
from app.modules.students.service import epoch
from app.core.contracts import Reason
from app.modules.verification.schemas import Version
from fastapi import APIRouter

router = APIRouter(tags=["verification"])


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
            from app.integrations.mock_apaar import MockApaarAdapter

            external_result = MockApaarAdapter().verify(student)
            status = external_result["status"]
            evidence = dict(
                label=external_result["label"],
                reasons=external_result["reasons"],
                reference=external_result["reference"],
            )
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

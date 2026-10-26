"""Verification HTTP operations."""

from app.modules.verification import repository
from app.core.http import idem
from uuid import UUID
from fastapi import Request
from app.db.session import connect
from app.core.errors import fail
from app.core.security import allow, student_scope, reason
from app.core.algorithms import valid_id
from app.core.contracts import Reason
from app.modules.verification.schemas import Version


def checks(student_id: UUID, body: Version, request: Request, user=None):
    allow(user, "OPERATOR", "OFFICER")
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)
        if student["version_no"] != body.expected_version:
            fail("VERSION_CONFLICT", 409)
        findings = repository.checks_verification_findings(conn, (student_id,))
        return dict(
            data_quality_status=student["data_quality_status"],
            external_status=student["external_status"],
            findings=findings,
            data_epoch=repository.checks_institution_epochs(conn, (student["institution_id"],))["data_epoch"],
        )


def external_check(student_id: UUID, body: Reason, request: Request, user=None):
    allow(user, "OFFICER")
    reason(body.reason)
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)
        if student["data_quality_status"] != "PASSED_LOCAL_CHECKS" or not valid_id(student["apaar_id"]):
            fail("LOCAL_CHECKS_REQUIRED", 409)

        def work(key):
            from app.modules.verification.external import verify_mock

            return verify_mock(conn, student, user, body.reason)

        return idem(conn, user, request, body.model_dump(), work)

"""Reviews HTTP operations."""

from app.modules.reviews import repository
from app.core.http import listing, pagination, idem
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from fastapi import Request
from app.settings import settings
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import allow, institution_scope, student_scope, reason
from app.core.algorithms import normalized_name
from app.core.audit import append
from app.modules.students.service import passport, trust_for, epoch
from app.core.contracts import Reason
from app.modules.reviews.schemas import Decision
from app.modules.reviews.schemas import CandidateDecision


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


def list_cases(
    status: str | None = None,
    institution_id: UUID | None = None,
    rule: str | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 25,
    user=None,
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


def case_detail(case_id: UUID, request: Request, user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    with connect() as conn:
        row = repository.case_detail_review_cases(conn, (case_id,))
        if not row:
            fail("NOT_FOUND", 404)
        if user["role_code"] == "ADMIN" and (not request.headers.get("x-case-access")):
            return dict(
                case=masked(row),
                masked=True,
                allowed_actions=["ACCESS_ESCALATED"] if row["status"] == "ESCALATED" else [],
            )
        student = student_scope(conn, user, row["student_id"], request, expected_case_id=case_id)
        findings = repository.case_detail_verification_findings(conn, (student["id"],))
        duplicates = repository.case_detail_duplicate_candidates(conn, (student["id"], student["id"]))
        source = repository.source_snapshot(conn, student["id"])
        submitted = source["normalized_data"] if source else student
        references = source["reference_snapshot"].get("rows", []) if source else []
        reference = next(
            (
                item
                for item in references
                if str(item.get("id")) != str(student["id"])
                and item.get("submitted_enrollment_no") == submitted.get("submitted_enrollment_no")
            ),
            None,
        )
        comparison = [
            dict(
                field=field,
                submitted=submitted.get(field),
                reference=(reference or {}).get(field),
                source_label="Frozen local reference snapshot" if reference else "No frozen reference available",
            )
            for field in ["submitted_apaar_id", "submitted_enrollment_no", "full_name", "dob", "parent_name"]
        ]
        actions = []
        if user["role_code"] in {"OFFICER", "ADMIN"} and row["status"] != "APPROVED":
            actions = ["REQUEST_CORRECTION", "ESCALATE"]
            if not findings and (not duplicates):
                actions.append("APPROVE")
        return dict(
            case={k: row[k] for k in ["id", "student_id", "status", "opened_reason", "version_no"]},
            student=passport(conn, student),
            findings=findings,
            comparison=comparison,
            duplicates=duplicates,
            versions=repository.case_detail_record_versions(conn, (student["id"],)),
            decisions=repository.case_detail_review_decisions(conn, (case_id,)),
            allowed_actions=actions,
        )


def case_access(case_id: UUID, body: Reason, user=None):
    allow(user, "ADMIN")
    reason(body.reason)
    with connect() as conn:
        case = repository.case_access_review_cases(conn, (case_id,))
        if not case:
            fail("NOT_FOUND", 404)
        if case["status"] != "ESCALATED":
            fail("CASE_NOT_ESCALATED", 409)
        repository.case_access_review_decisions(conn, (case_id, user["id"], body.reason, case["version_no"]))
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


def decide(case_id: UUID, body: Decision, request: Request, user=None):
    allow(user, "OFFICER", "ADMIN")
    reason(body.reason)
    with connect() as conn:

        def work(key):
            case = repository.work_review_cases(conn, (case_id,))
            if not case:
                fail("NOT_FOUND", 404)
            student = student_scope(conn, user, case["student_id"], request, expected_case_id=case_id)
            if case["version_no"] != body.expected_version:
                fail("VERSION_CONFLICT", 409)
            target = {"REQUEST_CORRECTION": "CORRECTION_REQUESTED", "ESCALATE": "ESCALATED", "APPROVE": "APPROVED"}.get(
                body.action
            )
            if (
                not target
                or case["status"] not in {"OPEN", "ESCALATED"}
                or (case["status"] == "ESCALATED" and target == "ESCALATED")
            ):
                fail("INVALID_TRANSITION", 409)
            if body.action == "REQUEST_CORRECTION" and (not body.requested_fields):
                fail("REQUESTED_FIELDS_REQUIRED")
            if body.action == "APPROVE":
                if repository.work_verification_findings(
                    conn, (student["id"],)
                ) or repository.work_duplicate_candidates(conn, (student["id"], student["id"])):
                    fail("UNRESOLVED_FINDINGS", 409)
            updated = repository.work_review_cases_2(conn, (target, target, case_id))
            decision = repository.work_review_decisions(
                conn, (case_id, user["id"], body.action, body.reason, updated["version_no"])
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


def candidate_decision(candidate_id: UUID, body: CandidateDecision, request: Request, user=None):
    allow(user, "OFFICER", "ADMIN")
    reason(body.reason)
    if body.action not in {"DISMISS_DUPLICATE", "CONFIRM_DUPLICATE"}:
        fail("INVALID_ACTION")
    with connect() as conn:

        def work(key):
            case = repository.work_review_cases_3(conn, (body.case_id,))
            candidate = repository.work_duplicate_candidates_2(conn, (candidate_id,))
            if not case or not candidate or case["student_id"] not in {candidate["student_a"], candidate["student_b"]}:
                fail("NOT_FOUND", 404)
            student = student_scope(conn, user, case["student_id"], request, expected_case_id=body.case_id)
            if case["version_no"] != body.expected_case_version or candidate["status"] != "OPEN":
                fail("VERSION_CONFLICT", 409)
            status = "DISMISSED" if body.action == "DISMISS_DUPLICATE" else "CONFIRMED"
            repository.work_duplicate_candidates_3(conn, (status, candidate_id))
            repository.work_review_cases_4(conn, (body.case_id,))
            repository.work_review_decisions_2(
                conn, (body.case_id, user["id"], body.action, body.reason, case["version_no"] + 1)
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

"""Reviews HTTP operations."""

from app.core.http import listing, pagination, idem
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from fastapi import Request, Depends
from app.settings import settings
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, institution_scope, student_scope, reason
from app.core.algorithms import normalized_name
from app.core.audit import append
from app.modules.students.service import passport, trust_for, epoch
from app.core.contracts import Reason
from app.modules.reviews.schemas import Decision
from app.modules.reviews.schemas import CandidateDecision
from fastapi import APIRouter

router = APIRouter(tags=["reviews"])


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

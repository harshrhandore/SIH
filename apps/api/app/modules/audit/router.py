"""Audit HTTP operations."""

from app.core.http import listing, pagination
from uuid import UUID
from fastapi import Request, Depends
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, institution_scope, student_scope
from app.core.audit import verify
from fastapi import APIRouter

router = APIRouter(tags=["audit"])


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

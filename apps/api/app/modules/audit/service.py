"""Audit append/verification and scoped read transaction policy."""

from app.core.clock import utc_stamp as stamp
from app.modules.audit.canonical import canonical as canonical, normalize as normalize
import hashlib
import json
from datetime import datetime
from uuid import uuid4
from app.modules.audit import repository
from app.modules.audit.sandbox import read_snapshot
from app.core.http import listing, pagination
from app.core.security import allow, institution_scope, student_scope
from app.core.errors import fail
from app.db.session import connect
from app.settings import settings
import hmac


def append(conn, institution, actor, action, entity_type, entity_id, reason, payload=None, student=None):
    chain = repository.lock_chain(conn, institution)
    event = dict(
        event_id=str(uuid4()),
        chain_id=str(chain["id"]),
        sequence_no=chain["head_seq"] + 1,
        institution_id=str(institution) if institution else None,
        student_id=str(student) if student else None,
        actor_id=str(actor),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        reason=reason,
        occurred_at=stamp(),
        payload=payload or {},
    )
    return repository.append_event(conn, chain["id"], canonical(event))


def verify(conn, institution, sandbox=False):
    if sandbox:
        snapshot = read_snapshot(conn, institution)
        chain = (snapshot or {}).get("chain")
        rows = (snapshot or {}).get("events") or []
    else:
        chain, rows = repository.production_snapshot(conn, institution)
    if not chain:
        return dict(valid=False, exists=False, first_broken_link=None, checked_at=stamp())
    if sandbox:
        for row in rows:
            row["occurred_at"] = datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
    previous = "0" * 64
    failure = None
    checked = 0
    for index, row in enumerate(rows, 1):
        envelope = dict(
            event_id=str(row["id"]),
            chain_id=str(row["chain_id"]),
            sequence_no=row["sequence_no"],
            institution_id=str(row["institution_id"]) if row["institution_id"] else None,
            student_id=str(row["student_id"]) if row["student_id"] else None,
            actor_id=str(row["actor_id"]),
            action=row["action"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            reason=row["reason"],
            occurred_at=stamp(row["occurred_at"]),
            payload=row["payload"],
        )
        cause = None
        if row["sequence_no"] != index:
            cause = "SEQUENCE_GAP"
        elif row["prev_hash"] != previous:
            cause = "PREVIOUS_HASH_MISMATCH"
        else:
            try:
                parsed = json.loads(row["canonical_text"])
                if canonical(parsed) != row["canonical_text"] or canonical(envelope) != row["canonical_text"]:
                    cause = "ENVELOPE_MISMATCH"
                elif hashlib.sha256((previous + row["canonical_text"]).encode()).hexdigest() != row["row_hash"]:
                    cause = "ROW_HASH_MISMATCH"
            except (ValueError, TypeError):
                cause = "INVALID_CANONICAL_TEXT"
        checked = index
        if cause:
            failure = dict(sequence_no=row["sequence_no"], event_id=str(row["id"]), reason=cause)
            break
        previous = row["row_hash"]
    if not failure and (len(rows) != chain["head_seq"] or previous != chain["head_hash"]):
        failure = dict(sequence_no=len(rows) + 1, event_id=None, reason="HEAD_MISMATCH")
    return dict(
        valid=failure is None,
        exists=True,
        chain_id=chain["id"],
        events_checked=checked,
        head_seq=chain["head_seq"],
        head_hash=chain["head_hash"],
        first_broken_link=failure,
        checked_at=stamp(),
        is_copy=sandbox,
        production_chain_modified=False,
    )


def student_timeline(student_id, request, page, page_size, user):
    offset = pagination(page, page_size)
    with connect() as conn:
        # Scope, grant state, chain head and event rows share one snapshot.
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        student = student_scope(conn, user, student_id, request)
        checked = verify(conn, student["institution_id"])
        rows, total = repository.timeline(conn, student_id, page_size, offset)
        for row in rows:
            row["hash_verified"] = checked["valid"]
            row["changes"] = row.pop("payload").get("changes", {})
        return listing(
            rows,
            total,
            page,
            page_size,
            chain_verified_at=checked["checked_at"],
            checked_head_seq=checked.get("head_seq"),
            verified=checked["valid"],
        )


def chain_summary(institution_id, user):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    institution_scope(user, institution_id, admin=True)
    with connect() as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return verify(conn, institution_id)


def events(request, institution_id, case_id, page, page_size, user):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    ids = institution_scope(user, institution_id, admin=True)
    offset = pagination(page, page_size)
    admin = user["role_code"] == "ADMIN"
    grant = request.headers.get("x-case-access")
    if admin and grant and not case_id:
        fail("CASE_FILTER_REQUIRED", 403, "Case access cannot authorize a broad raw audit request.")
    with connect() as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        student_id = None
        if case_id:
            case = repository.case_owner(conn, case_id)
            if not case:
                fail("NOT_FOUND", 404)
            if not admin or grant:
                student_scope(conn, user, case["student_id"], request, expected_case_id=case_id)
            if institution_id and case["institution_id"] != institution_id:
                fail("INVALID_FILTER_COMBINATION", 422)
            student_id = case["student_id"]
        rows, total = repository.event_page(
            conn, ids, student_id, not admin or bool(grant and case_id), page_size, offset
        )
        if case_id:
            reference = hmac.new(
                settings.mask_secret.encode(), ("case:" + str(case_id)).encode(), hashlib.sha256
            ).hexdigest()[:12]
            for row in rows:
                row["case_ref"] = reference
        return listing(rows, total, page, page_size)

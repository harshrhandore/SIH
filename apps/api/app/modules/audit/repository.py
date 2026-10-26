"""Fixed SQL for immutable chain reads and serialized appends."""

from typing import cast
from app.db.models import AuditChainRow, AuditEventRow
from app.db.session import one, many


def lock_chain(conn, institution) -> AuditChainRow:
    return cast(AuditChainRow, one(conn, "SELECT * FROM lock_audit_chain(%s)", (institution,)))


def append_event(conn, chain_id, canonical_text):
    return one(conn, "SELECT * FROM append_audit(%s,%s)", (chain_id, canonical_text))


def production_snapshot(conn, institution) -> tuple[AuditChainRow | None, list[AuditEventRow]]:
    chain = cast(
        AuditChainRow | None,
        one(
            conn, "SELECT * FROM public.audit_chains WHERE institution_id IS NOT DISTINCT FROM %s::uuid", (institution,)
        ),
    )
    rows = (
        cast(
            list[AuditEventRow],
            many(conn, "SELECT * FROM public.audit_events WHERE chain_id=%s ORDER BY sequence_no", (chain["id"],)),
        )
        if chain
        else []
    )
    return chain, rows


def timeline(conn, student_id, limit, offset):
    rows = many(
        conn,
        "SELECT e.id AS event_id,e.action,e.occurred_at,e.reason,e.payload,e.sequence_no,e.row_hash,u.full_name AS actor_name FROM audit_events e JOIN users u ON u.id=e.actor_id WHERE e.student_id=%s ORDER BY e.sequence_no DESC LIMIT %s OFFSET %s",
        (student_id, limit, offset),
    )
    total = one(conn, "SELECT count(*) AS n FROM audit_events WHERE student_id=%s", (student_id,))["n"]
    return rows, total


def case_owner(conn, case_id):
    return one(
        conn,
        "SELECT c.id,c.student_id,s.institution_id FROM review_cases c JOIN students s ON s.id=c.student_id WHERE c.id=%s",
        (case_id,),
    )


def event_page(conn, institutions, student_id, include_reason, limit, offset):
    columns = "id AS event_id,action,occurred_at" + (",reason" if include_reason else "")
    predicate = "(%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[])) AND (%s::uuid IS NULL OR student_id=%s)"
    params = (institutions, institutions, student_id, student_id)
    rows = many(
        conn,
        "SELECT "
        + columns
        + " FROM audit_events WHERE "
        + predicate
        + " ORDER BY occurred_at DESC,id DESC LIMIT %s OFFSET %s",
        params + (limit, offset),
    )
    total = one(conn, "SELECT count(*) AS n FROM audit_events WHERE " + predicate, params)["n"]
    return rows, total

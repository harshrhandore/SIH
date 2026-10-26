"""Scoped read broker and owner-only isolated copy lifecycle."""

import json
from app.settings import settings
from app.db.session import connect, one


def read_snapshot(conn, institution):
    return one(conn, "SELECT demo_sandbox_snapshot(%s) AS snapshot", (institution,))["snapshot"]


def manage(owner_url, inst, action):
    from app.modules.audit.service import verify

    if not settings.demo_controls_enabled:
        raise RuntimeError("Demo controls disabled")
    with connect(owner_url) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if action in {"create", "restore"}:
            conn.execute("CREATE SCHEMA IF NOT EXISTS demo_sandbox")
            conn.execute("DROP TABLE IF EXISTS demo_sandbox.audit_events,demo_sandbox.audit_chains")
            conn.execute(
                "CREATE TABLE demo_sandbox.audit_chains AS SELECT * FROM public.audit_chains WHERE institution_id=%s",
                (inst,),
            )
            conn.execute(
                "CREATE TABLE demo_sandbox.audit_events AS SELECT * FROM public.audit_events WHERE institution_id=%s",
                (inst,),
            )
        elif action == "tamper":
            row = one(
                conn,
                "SELECT * FROM demo_sandbox.audit_events WHERE action='REVIEW_APPROVED' ORDER BY sequence_no DESC LIMIT 1",
            )
            if not row:
                raise RuntimeError("Create sandbox after a review approval")
            parsed = json.loads(row["canonical_text"])
            parsed["reason"] = "TAMPERED SYNTHETIC DEMO"
            from app.modules.audit.canonical import canonical

            conn.execute(
                "UPDATE demo_sandbox.audit_events SET reason=%s,canonical_text=%s WHERE chain_id=%s AND sequence_no=%s",
                (parsed["reason"], canonical(parsed), row["chain_id"], row["sequence_no"]),
            )
        return verify(conn, inst, True)

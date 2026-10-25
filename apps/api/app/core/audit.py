import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from uuid import uuid4
from app.db.session import one, many


def normalize(value):
    if isinstance(value, float):
        raise ValueError("Floats are forbidden in canonical events")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("Canonical object keys must be strings")
        return {normalize(k): normalize(v) for k, v in value.items()}
    if value is None or isinstance(value, (int, bool)):
        return value
    raise ValueError(f"Unsupported canonical type {type(value).__name__}")


def canonical(value):
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def stamp(value=None):
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def append(conn, institution, actor, action, entity_type, entity_id, reason, payload=None, student=None):
    chain = one(conn, "SELECT * FROM lock_audit_chain(%s)", (institution,))
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
    return one(conn, "SELECT * FROM append_audit(%s,%s)", (chain["id"], canonical(event)))


def verify(conn, institution, sandbox=False):
    # Fixed identifiers only. Never accept a schema from an HTTP caller.
    chains = "demo_sandbox.audit_chains" if sandbox else "public.audit_chains"
    events = "demo_sandbox.audit_events" if sandbox else "public.audit_events"
    chain = one(conn, f"SELECT * FROM {chains} WHERE institution_id=%s", (institution,))
    if not chain:
        return dict(valid=False, exists=False, first_broken_link=None, checked_at=stamp())
    rows = many(conn, f"SELECT * FROM {events} WHERE chain_id=%s ORDER BY sequence_no", (chain["id"],))
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

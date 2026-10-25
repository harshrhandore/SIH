"""Shared pagination, import scope and transactional mutation replay."""

import hashlib
import json
from uuid import UUID
from psycopg.types.json import Jsonb
from app.core.errors import fail
from app.core.security import allow, scope_ids
from app.db.session import one
from app.core.serialization import jsonable


def listing(items, total=None, page=1, page_size=25, **extra):
    return dict(items=items, total=len(items) if total is None else total, page=page, page_size=page_size, **extra)


def pagination(page, size):
    if page < 1 or size not in {25, 50}:
        fail("INVALID_PAGINATION")
    if (page - 1) * size > 10000:
        fail("OFFSET_LIMIT")
    return (page - 1) * size


def batch_scope(conn, user, batch_id):
    allow(user, "OPERATOR", "OFFICER")
    batch = one(conn, "SELECT * FROM import_batches WHERE id=%s", (batch_id,))
    if not batch or batch["institution_id"] not in scope_ids(user):
        fail("NOT_FOUND", 404)
    return batch


def idem(conn, user, request, body, work):
    raw = request.headers.get("idempotency-key")
    try:
        key = UUID(raw or "")
    except ValueError:
        fail("IDEMPOTENCY_KEY_REQUIRED")
    digest = hashlib.sha256(json.dumps(jsonable(body), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(user["id"]) + str(key),))
    old = one(conn, "SELECT * FROM api_idempotency WHERE actor_id=%s AND key=%s", (user["id"], key))
    operation = request.method + " " + request.url.path
    if old:
        if old["request_hash"] != digest or old["operation"] != operation:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return old["response_body"]
    result = jsonable(work(key))
    conn.execute(
        "INSERT INTO api_idempotency(actor_id,key,operation,request_hash,response_status,response_body) VALUES (%s,%s,%s,%s,200,%s)",
        (user["id"], key, operation, digest, Jsonb(result)),
    )
    return result

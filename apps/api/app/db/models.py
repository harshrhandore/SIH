"""Database read shapes shared by audit persistence and verification."""

from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID


class AuditChainRow(TypedDict):
    id: UUID
    institution_id: UUID | None
    name: str
    head_seq: int
    head_hash: str


class AuditEventRow(TypedDict):
    id: UUID
    chain_id: UUID
    sequence_no: int
    institution_id: UUID | None
    student_id: UUID | None
    actor_id: UUID
    action: str
    entity_type: str
    entity_id: str
    reason: str
    occurred_at: datetime
    payload: dict[str, Any]
    canonical_text: str
    prev_hash: str
    row_hash: str

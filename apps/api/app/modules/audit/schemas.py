from datetime import datetime
from typing import Annotated, Any
from uuid import UUID
from pydantic import BaseModel, Field, PlainSerializer
from app.core.clock import utc_stamp

Timestamp = Annotated[datetime, PlainSerializer(utc_stamp, return_type=str, when_used="json")]


class BrokenLink(BaseModel):
    sequence_no: int
    event_id: UUID | None
    reason: str


class ChainVerification(BaseModel):
    valid: bool
    exists: bool
    checked_at: Timestamp
    first_broken_link: BrokenLink | None
    chain_id: UUID | None = None
    events_checked: int | None = None
    head_seq: int | None = None
    head_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    is_copy: bool = False
    production_chain_modified: bool = False


class TimelineEvent(BaseModel):
    event_id: UUID
    action: str
    occurred_at: Timestamp
    actor_name: str
    reason: str
    changes: dict[str, Any]
    sequence_no: int
    row_hash: str
    hash_verified: bool


class TimelineResponse(BaseModel):
    items: list[TimelineEvent]
    total: int
    page: int
    page_size: int
    chain_verified_at: Timestamp
    checked_head_seq: int | None
    verified: bool


class EventSummary(BaseModel):
    event_id: UUID
    action: str
    occurred_at: Timestamp
    reason: str | None = None
    case_ref: str | None = None


class EventsResponse(BaseModel):
    items: list[EventSummary]
    total: int
    page: int
    page_size: int

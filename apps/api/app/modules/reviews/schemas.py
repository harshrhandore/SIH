"""Reviews request contracts."""

from uuid import UUID
from pydantic import Field
from app.core.contracts import Reason


class Decision(Reason):
    expected_version: int = Field(ge=1)
    action: str
    requested_fields: list[str] = []


class CandidateDecision(Reason):
    action: str
    case_id: UUID
    expected_case_version: int = Field(ge=1)

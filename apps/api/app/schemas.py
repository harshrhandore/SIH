from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: Literal["OPERATOR", "OFFICER", "ADMIN", "STUDENT"]
    institution_id: UUID | None
    student_id: UUID | None
    assigned_institutions: list[UUID]


class StudentSummary(BaseModel):
    id: UUID
    full_name: str | None
    apaar_id: str | None
    institution_id: UUID
    program: str | None
    branch: str | None
    current_year: int | None
    data_quality_status: Literal["PASSED_LOCAL_CHECKS", "FLAGGED_FOR_REVIEW", "INCOMPLETE"]
    external_status: Literal["EXTERNAL_VERIFICATION_PENDING", "MOCK_MATCH", "MOCK_NO_MATCH"]
    version_no: int


class SearchResponse(BaseModel):
    items: list[StudentSummary]
    total: int
    page: int
    page_size: int
    took_ms: float
    cache: Literal["HIT", "MISS"]
    data_epoch: int

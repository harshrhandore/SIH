"""Career request contracts."""

from pydantic import Field
from app.core.contracts import Strict
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class Career(Strict):
    question: str = Field(min_length=1, max_length=1000)
    role_code: str | None = None


class Evidence(BaseModel):
    kind: str
    id: UUID
    title: str | None


class SkillWeight(BaseModel):
    code: str
    weight: int


class MissingSkill(SkillWeight):
    label: str


class MatchedSkill(MissingSkill):
    evidence: list[Evidence]


class Step(BaseModel):
    priority: int
    action: str
    estimated_weeks: int
    reason: str


class Course(BaseModel):
    title: str
    provider: str
    url: str | None


class CareerResult(BaseModel):
    role_code: str
    readiness_percent: int = Field(ge=0, le=100)
    matched_skills: list[MatchedSkill]
    missing_skills: list[MissingSkill]
    recommended_steps: list[Step]
    suggested_courses: list[Course]
    explanation: str
    phrasing_source: Literal["RULE_BASED", "GEMINI"]
    catalogue_version: Literal[1]


class CareerResponse(CareerResult):
    session_id: UUID


class HistoryItem(BaseModel):
    session_id: UUID
    question: str
    role_code: str
    readiness_percent: int = Field(ge=0, le=100)
    response: CareerResult
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int


class Role(BaseModel):
    code: str
    label: str
    skills: list[SkillWeight]


class RolesResponse(BaseModel):
    catalogue_version: Literal[1]
    roles: list[Role]

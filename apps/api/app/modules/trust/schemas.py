from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TrustInputs(BaseModel):
    complete_fields: int
    errors: int
    warnings: int
    missing_mandatory: bool
    certificates: int
    approved: bool
    risk: int


class TrustComponent(BaseModel):
    key: Literal["completeness", "local", "certificates", "fraud", "review", "external"]
    earned: float
    max: int
    reason: str
    raw_inputs: TrustInputs


class TrustResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    maximum: Literal[100]
    components: list[TrustComponent]
    formula_version: Literal[1]
    officially_verified: Literal[False]
    student_version: int
    computed_at: datetime

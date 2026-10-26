"""Validate bootstrap output and publish the same contract as JSON Schema."""

from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SeedManifest(BaseModel):
    model_config = ConfigDict(extra="allow")
    seed: Literal[2026263]
    clock: date
    showcase_student_id: UUID
    showcase_apaar_id: Annotated[str, Field(pattern=r"^SYN-[0-9]{13}$")]
    institution_a_id: UUID
    correction_row: int = Field(ge=1)
    correct_to: Annotated[str, Field(pattern=r"^SYN-[0-9]{13}$")]
    correction_enrollment: str
    expected_import: dict[str, NonNegativeInt]
    fixture_import: Literal["demo-import-1000.csv"]
    showcase_readiness: int = Field(ge=0, le=100)
    showcase_trust: int = Field(ge=0, le=100)
    hashes: dict[str, Digest]
    dataset_students: Literal[200, 5000, 50000, 100000]
    institution_counts: list[NonNegativeInt]
    seed_seconds: float = Field(ge=0)
    total_seconds: float = Field(ge=0)
    database_bytes: NonNegativeInt
    seed_validation: dict[str, Any]

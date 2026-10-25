from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class Institution(BaseModel):
    id: UUID
    name: str
    state: str
    aicte_code: str


class Program(BaseModel):
    id: UUID
    institution_id: UUID
    level: Literal["BTECH", "PGDM"]
    name: str
    branch: str
    duration_years: int
    term_type: Literal["SEMESTER", "TRIMESTER"]
    total_terms: int
    intake: int


class InstitutionsResponse(BaseModel):
    items: list[Institution]
    total: int
    page: int
    page_size: int


class ProgramsResponse(BaseModel):
    items: list[Program]
    total: int
    page: int
    page_size: int

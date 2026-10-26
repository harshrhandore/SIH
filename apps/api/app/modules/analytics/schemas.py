from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: date
    clean_percent: float | None


class AdmissionsRow(BaseModel):
    institution_id: UUID
    program_id: UUID
    year: int
    admitted: int


class PlacementRow(BaseModel):
    institution_id: UUID
    program_id: UUID
    year: int
    eligible_students: int
    placed_students: int
    placement_rate: float | None
    median_package_lpa: float | None
    max_package_lpa: float | None


class PerformanceRow(BaseModel):
    institution_id: UUID
    program_id: UUID
    branch: str
    year: int
    assessed_students: int
    avg_cgpa: float | None
    pass_percent: float | None
    bucket_0_4: int
    bucket_4_6: int
    bucket_6_8: int
    bucket_8_10: int


class QualityRow(BaseModel):
    institution_id: UUID
    program_id: UUID | None = None
    expected_records: int | None = None
    total: int
    clean: int
    flagged: int
    incomplete: int
    external_pending: int
    submission_percent: float
    missing_records: int
    pending_reviews: int


class AnalyticsResponse(BaseModel):
    items: list[AdmissionsRow | PlacementRow | PerformanceRow | QualityRow]
    trend: list[TrendPoint]
    took_ms: float
    data_as_of: datetime | None
    refreshing: bool
    stale: bool


class OversightRow(BaseModel):
    institution_id: UUID
    institution_name: str
    state: str
    total: int
    submission_percent: float
    missing_records: int
    unresolved_discrepancies: int
    pending_reviews: int


class OversightResponse(BaseModel):
    items: list[OversightRow]
    total: int
    page: int
    page_size: int
    trend: list[TrendPoint]


class RefreshView(BaseModel):
    name: str
    status: str
    refreshed_at: datetime | None
    source_epoch: int


class RefreshStatus(BaseModel):
    status: str
    views: list[RefreshView]
    stale: bool


class RefreshQueued(BaseModel):
    status: str
    poll_url: str

"""Demo request contracts."""

from pydantic import Field
from app.core.contracts import Strict


class SessionControls(Strict):
    cache_enabled: bool


class BenchmarkRequest(Strict):
    dataset: str = "current"
    runs: int = Field(default=20, ge=20, le=100)
    cache_mode: str = "BOTH"

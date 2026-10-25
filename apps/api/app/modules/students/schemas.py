"""Students request contracts."""

from pydantic import Field
from app.core.contracts import Reason


class Patch(Reason):
    expected_version: int = Field(ge=1)
    patch: dict

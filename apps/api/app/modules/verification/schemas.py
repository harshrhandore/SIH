"""Verification request contracts."""

from pydantic import Field
from app.core.contracts import Strict


class Version(Strict):
    expected_version: int = Field(ge=1)

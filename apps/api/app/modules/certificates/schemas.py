"""Certificates request contracts."""

from uuid import UUID
from app.core.contracts import Strict
from app.core.contracts import Reason


class VerifyAlias(Strict):
    certificate_id: UUID


class Acceptance(Reason):
    action: str

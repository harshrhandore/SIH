"""Compatibility imports for existing audit callers."""

from app.core.clock import utc_stamp as stamp
from app.modules.audit.canonical import canonical as canonical, normalize as normalize
from app.modules.audit.service import append as append, verify as verify

__all__ = ["stamp", "canonical", "normalize", "append", "verify"]

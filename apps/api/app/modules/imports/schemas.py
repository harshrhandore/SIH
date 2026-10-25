"""Imports request contracts."""

from app.core.contracts import Strict


class Mapping(Strict):
    mapping: dict[str, str]
    date_format: str = "DD/MM/YYYY"


class Confirm(Strict):
    confirm_synthetic_data: bool

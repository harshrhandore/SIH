"""Allowlisted request telemetry: no URL, identity, headers or request bodies."""

import json
import logging

logger = logging.getLogger("shiksham.requests")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def log_request(request_id: str, status: int, duration_seconds: float):
    logger.info(json.dumps(dict(request_id=request_id, status=status, took_ms=round(duration_seconds * 1000, 3))))

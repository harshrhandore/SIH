"""NFC canonical event encoding, excluding floats and unsupported types."""

import json
import unicodedata


def normalize(value):
    if isinstance(value, float):
        raise ValueError("Floats are forbidden in canonical events")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("Canonical object keys must be strings")
        return {normalize(k): normalize(v) for k, v in value.items()}
    if value is None or isinstance(value, (int, bool)):
        return value
    raise ValueError(f"Unsupported canonical type {type(value).__name__}")


def canonical(value):
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

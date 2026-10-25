from pathlib import Path
from uuid import uuid4
import hashlib
from app.core.errors import fail
from app.settings import ROOT, settings


def root_path(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def contained(root, key):
    base = Path(root).resolve()
    path = (base / key).resolve()
    if not path.is_relative_to(base):
        fail("NOT_FOUND", 404)
    return path


def store(data, institution, student, suffix):
    key = f"{institution}/{student}/{uuid4()}.{suffix}"
    path = contained(root_path(settings.storage_root), key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key, hashlib.sha256(data).hexdigest()


def read(key):
    path = contained(root_path(settings.storage_root), key)
    if not path.exists():
        fail("MISSING_FILE", 404, "Stored file is unavailable. Re-upload the synthetic file.")
    return path

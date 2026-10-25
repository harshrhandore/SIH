from fastapi import HTTPException
from typing import NoReturn


def fail(code, status=422, message=None, fields=None) -> NoReturn:
    raise HTTPException(
        status, {"code": code, "message": message or code.replace("_", " ").capitalize(), "fields": fields or []}
    )

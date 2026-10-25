"""Bounded passive-document inspection and explicit labelled-field extraction."""

import re
from io import BytesIO
from typing import cast
import filetype
from pypdf import PdfReader
from pypdf.generic import DictionaryObject
from PIL import Image
from app.core.errors import fail


def inspect_document(data):
    if len(data) > 10 * 1024 * 1024:
        fail("FILE_TOO_LARGE", 413)
    kind = filetype.guess(data)
    if not kind or kind.mime not in {"application/pdf", "image/png", "image/jpeg"}:
        fail("UNSUPPORTED_MEDIA_TYPE", 415)
    if kind.mime == "application/pdf":
        try:
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted or len(reader.pages) > 10:
                fail("UNSUPPORTED_DOCUMENT")
            root = cast(DictionaryObject, reader.trailer["/Root"])
            visited = set()

            def reject_active(obj):
                obj = obj.get_object() if hasattr(obj, "get_object") else obj
                if id(obj) in visited:
                    return
                visited.add(id(obj))
                if isinstance(obj, dict):
                    if any(
                        str(k)
                        in {
                            "/OpenAction",
                            "/AA",
                            "/JavaScript",
                            "/JS",
                            "/EmbeddedFiles",
                            "/EmbeddedFile",
                            "/Launch",
                            "/RichMedia",
                            "/XFA",
                        }
                        for k in obj
                    ):
                        fail("UNSUPPORTED_DOCUMENT")
                    if str(obj.get("/S", "")) in {
                        "/JavaScript",
                        "/Launch",
                        "/SubmitForm",
                        "/ImportData",
                        "/GoToR",
                        "/URI",
                    }:
                        fail("UNSUPPORTED_DOCUMENT")
                    for value in obj.values():
                        reject_active(value)
                elif isinstance(obj, list):
                    for value in obj:
                        reject_active(value)

            reject_active(root)
            if (
                any(token in root for token in ["/OpenAction", "/AA"])
                or b"/JavaScript" in data
                or b"/EmbeddedFile" in data
                or b"/Launch" in data
            ):
                fail("UNSUPPORTED_DOCUMENT")
        except Exception as exc:
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                raise
            fail("UNSUPPORTED_DOCUMENT")
    else:
        try:
            image = Image.open(BytesIO(data))
            if image.width * image.height > 40_000_000:
                fail("UNSUPPORTED_DOCUMENT")
            image.verify()
        except Exception:
            fail("UNSUPPORTED_DOCUMENT")
    return kind.mime, "jpg" if kind.mime == "image/jpeg" else kind.extension


def fields_from_text(text):
    fields = {}
    for key, label in [
        ("name", "Name"),
        ("certificate", "Certificate"),
        ("issuer", "Issued by"),
        ("date", "Date"),
        ("credential_id", "Credential"),
    ]:
        match = re.search(r"^[ \t]*" + label + r":[ \t]*([^\r\n]{0,300})", text, re.M | re.I)
        fields[key] = (match.group(1).strip() or None) if match else None
    return fields

from datetime import datetime
from io import BytesIO
import re
import shutil
from time import perf_counter
from uuid import uuid4
from typing import cast
from pypdf.generic import DictionaryObject
import filetype
from pypdf import PdfReader
from PIL import Image
from psycopg.types.json import Jsonb
from app.core.algorithms import certificate_confidence
from app.core.errors import fail
from app.core.files import store
from app.core.audit import append
from app.db.session import one
from app.settings import ROOT, settings
from app.core.weights import load_weights


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


def extract_text(data, mime):
    warnings: list[str] = []
    metadata = {}
    text = ""
    image = None
    if mime == "application/pdf":
        reader = PdfReader(BytesIO(data))
        metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        if len("".join(text.split())) >= 50 and all(
            label in text for label in ["Name:", "Issued by:", "Date:", "Credential:"]
        ):
            return text[:16000], "PDF_TEXT", metadata, warnings
        import pypdfium2

        doc = pypdfium2.PdfDocument(data)
        page = doc[0]
        if page.get_width() * page.get_height() * (150 / 72) ** 2 > 40_000_000:
            fail("UNSUPPORTED_DOCUMENT")
        image = page.render(scale=150 / 72).to_pil()
    else:
        image = Image.open(BytesIO(data))
    if shutil.which("tesseract"):
        import pytesseract

        try:
            return pytesseract.image_to_string(image, timeout=15)[:16000], "TESSERACT", metadata, warnings
        except RuntimeError:
            warnings.append("Tesseract timed out or failed.")
    warnings.append("No available OCR engine produced readable text.")
    return "", "UNAVAILABLE", metadata, warnings


def fields_from_text(text):
    fields = {}
    for key, label in [
        ("name", "Name"),
        ("certificate", "Certificate"),
        ("issuer", "Issued by"),
        ("date", "Date"),
        ("credential_id", "Credential"),
    ]:
        match = re.search(r"^\s*" + label + r":\s*([^\r\n]{1,300})", text, re.M | re.I)
        fields[key] = match.group(1).strip() if match else None
    return fields


def evaluate(data, mime, student, reuse=None):
    start = perf_counter()
    text, engine, metadata, warnings = extract_text(data, mime)
    extracted = fields_from_text(text)
    from app.integrations.gemini import extract
    llm_fields=extract(text) if text else None
    if llm_fields:
        extracted=llm_fields
    confidence, matches, guard = certificate_confidence(extracted, student, settings.demo_as_of)
    reasons = []
    weights = load_weights("fraud")

    def add(code, weight, expected, observed, method):
        weight = weights.get("NAME_PARTIAL" if code == "NAME_MISMATCH" and weight == 35 else code, weight)
        reasons.append(
            dict(
                code=code,
                label=code.replace("_", " ").title(),
                weight=weight,
                severity="high" if weight >= 60 else "supporting",
                evidence=dict(
                    page=1,
                    field=code,
                    expected=expected,
                    observed=observed,
                    method=method,
                    limitations="Heuristic, not validated on real data.",
                ),
            )
        )

    n = matches["name"]
    if extracted["name"] and n < 0.90:
        add(
            "NAME_MISMATCH",
            65 if n < 0.70 else 35,
            student["full_name"],
            extracted["name"],
            "Normalized token matching",
        )
    elif not extracted["name"]:
        add("NAME_MISSING", 25, "Explicit name label", None, "Label extraction")
    created = metadata.get("/CreationDate", "")
    modified = metadata.get("/ModDate", "")
    try:
        if (
            datetime.strptime(modified[2:16], "%Y%m%d%H%M%S") - datetime.strptime(created[2:16], "%Y%m%d%H%M%S")
        ).total_seconds() > 86400:
            add("PDF_EDIT_METADATA", 10, created, modified, "PDF metadata timestamps")
    except ValueError:
        warnings.append("PDF modification interval not assessed.")
    tool = " ".join([metadata.get("/Creator", ""), metadata.get("/Producer", "")])
    if any(word in tool.casefold() for word in ["libreoffice", "photoshop", "gimp"]):
        add("PDF_EDITOR_TOOL", 8, "No editor indicator", tool, "PDF metadata")
    for code, weight in reuse or []:
        add(
            code,
            weight,
            "Evidence owned by this student",
            "Evidence also belongs to another student",
            "Scoped database reuse lookup",
        )
    risk = min(100, sum(r["weight"] for r in reasons))
    level = "high" if risk >= 60 else "medium" if risk >= 30 else "low"
    verified = bool(
        text
        and n >= 0.90
        and guard
        and matches["date"] == 1
        and matches["credential_id"] > 0
        and confidence >= 85
        and risk < 30
    )
    verdict = (
        "UNREADABLE"
        if not text
        else "VERIFIED_LOCAL"
        if verified
        else "NEEDS_REVIEW"
        if not extracted["name"]
        else "REJECTED"
        if n < 0.70 or risk >= 60
        else "NEEDS_REVIEW"
    )
    return dict(
        verified=verified,
        verdict=verdict,
        official=False,
        confidence=confidence if text else 0,
        extracted=extracted,
        matches=matches,
        risk=dict(level=level, score=risk, reasons=reasons),
        reasons=[
            dict(
                code="LOCAL_CONSISTENCY_ONLY",
                message="Matches synthetic records only; not issuer or official verification.",
            )
        ],
        ocr_engine=engine,
        extraction_source="GEMINI" if llm_fields else "RULE_BASED" if text else "UNAVAILABLE",
        warnings=warnings,
        metadata=metadata,
        not_assessed=[
            "Visual pHash reuse",
            "Image ELA",
            "Image noise",
            "Image blur",
            "PDF revision structure",
            "PDF font diversity",
        ],
        elapsed_ms=round((perf_counter() - start) * 1000, 3),
        heuristic_label="Heuristic, not validated",
    )


def persist_report(conn, certificate, student, result, key, actor):
    vid = uuid4()
    conn.execute(
        "INSERT INTO certificate_verifications(id,certificate_id,idempotency_key,ocr_engine,extraction_source,extracted_json,match_scores,confidence,verdict,risk,risk_score,reasons,file_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            vid,
            certificate["id"],
            key,
            result["ocr_engine"],
            result["extraction_source"],
            Jsonb(result["extracted"]),
            Jsonb(result["matches"]),
            result["confidence"],
            result["verdict"],
            result["risk"]["level"],
            result["risk"]["score"],
            Jsonb(result),
            certificate["file_sha256"],
        ),
    )
    conn.execute(
        "UPDATE certificates SET processing_status='DONE',issuer=%s,credential_id=%s WHERE id=%s",
        (result["extracted"]["issuer"], result["extracted"]["credential_id"], certificate["id"]),
    )
    append(
        conn,
        student["institution_id"],
        actor,
        "CERTIFICATE_VERIFIED",
        "certificate",
        certificate["id"],
        "Computed local certificate consistency.",
        dict(verdict=result["verdict"], confidence=str(result["confidence"]), risk=result["risk"]["score"]),
        student["id"],
    )
    return {
        **result,
        "verification_id": vid,
        "certificate_id": certificate["id"],
        "purpose": certificate["purpose"],
        "trust_effect": "EXCLUDED_TRIAL" if certificate["purpose"] == "TRIAL" else "PASSPORT_EVIDENCE",
        "created_at": str(datetime.now().astimezone()),
    }


def seed_certificates(conn):
    from db.seed.fixtures import uid

    student = one(conn, "SELECT * FROM students WHERE id=%s", (uid("student", 1),))
    for filename, title in [
        ("showcase-genuine.pdf", "Data Science Foundations"),
        ("showcase-python.pdf", "Python Fundamentals"),
    ]:
        data = (ROOT / "fixtures/certificates" / filename).read_bytes()
        key, sha = store(data, student["institution_id"], student["id"], "pdf")
        cid = uuid4()
        conn.execute(
            "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,acceptance_status,created_by) VALUES (%s,%s,%s,%s,%s,'application/pdf','PASSPORT','ACCEPTED',%s)",
            (cid, student["id"], title, key, sha, uid("user", "operator_a")),
        )
        certificate = one(conn, "SELECT * FROM certificates WHERE id=%s", (cid,))
        persist_report(
            conn, certificate, student, evaluate(data, "application/pdf", student), uuid4(), uid("user", "operator_a")
        )

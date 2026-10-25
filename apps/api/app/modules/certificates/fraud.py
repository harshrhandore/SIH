"""Local consistency verdicts and configured heuristic risk evidence."""

from datetime import datetime
from time import perf_counter
from app.core.algorithms import certificate_confidence
from app.core.weights import load_weights
from app.settings import settings
from app.modules.certificates.ocr import extract_text
from app.modules.certificates.extract import fields_from_text


def evaluate(data, mime, student, reuse=None, actor=None):
    start = perf_counter()
    text, engine, metadata, warnings = extract_text(data, mime)
    extracted = fields_from_text(text)
    from app.integrations.gemini import extract

    llm_fields = extract(text, actor) if text else None
    if llm_fields:
        extracted = llm_fields
    confidence, matches, guard = certificate_confidence(extracted, student, settings.demo_as_of)
    reasons = []
    weights = load_weights("fraud")
    thresholds = weights["thresholds"]

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
    if extracted["name"] and n < weights["name_verify"]:
        add(
            "NAME_MISMATCH",
            65 if n < weights["name_reject"] else 35,
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
    level = "high" if risk >= thresholds["high"] else "medium" if risk >= thresholds["medium"] else "low"
    verified = bool(
        text
        and n >= weights["name_verify"]
        and guard
        and matches["date"] == 1
        and matches["credential_id"] > 0
        and confidence >= weights["minimum_confidence"]
        and risk < thresholds["medium"]
    )
    verdict = (
        "UNREADABLE"
        if not text
        else "VERIFIED_LOCAL"
        if verified
        else "NEEDS_REVIEW"
        if not extracted["name"]
        else "REJECTED"
        if n < weights["name_reject"] or risk >= thresholds["high"]
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

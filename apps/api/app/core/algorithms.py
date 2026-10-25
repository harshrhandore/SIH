"""Version-one deterministic algorithms for synthetic records only."""

import re
import unicodedata
from typing import Any
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from rapidfuzz import fuzz
from unidecode import unidecode
from app.core.weights import load_weights

MISSING = {"", "na", "n/a", "null", "none", "-"}


def clean(value):
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value)).strip()
    return None if text.casefold() in MISSING else text


def normalized_name(value):
    text = unicodedata.normalize("NFC", value or "").casefold()
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    tokens = text.split()
    while tokens and tokens[0] in {"mr", "mrs", "ms", "dr"}:
        tokens.pop(0)
    return " ".join(tokens)


def name_match(a, b):
    x, y = normalized_name(a), normalized_name(b)
    if not x or not y:
        return 0.0, False
    score = max(fuzz.token_set_ratio(x, y), fuzz.token_set_ratio(unidecode(x), unidecode(y)))
    guard = min(len(x.split()), len(y.split())) / max(len(x.split()), len(y.split())) >= 0.67
    guard = guard and (
        x == y or max(fuzz.token_sort_ratio(x, y), fuzz.token_sort_ratio(unidecode(x), unidecode(y))) >= 85
    )
    return score, guard


def luhn(digits):
    return (
        sum(
            (int(c) * 2 - 9 if int(c) * 2 > 9 else int(c) * 2) if i % 2 else int(c)
            for i, c in enumerate(reversed(digits))
        )
        % 10
    )


def synthetic_id(counter):
    base = f"{counter:012d}"
    return "SYN-" + base + str((10 - luhn(base + "0")) % 10)


def valid_id(value):
    return bool(value and re.fullmatch(r"SYN-[0-9]{13}", value) and luhn(value[4:]) == 0)


def money_round(value, places="0.01"):
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def academic_cgpas(terms):
    weighted, credits = Decimal(0), Decimal(0)
    out = []
    for sgpa, credit in terms:
        weighted += Decimal(str(sgpa)) * Decimal(str(credit))
        credits += Decimal(str(credit))
        out.append(money_round(weighted / credits))
    return out


def possible_match(a, b):
    n, guard = name_match(a.get("full_name"), b.get("full_name"))
    p = (
        name_match(a.get("parent_name"), b.get("parent_name"))[0]
        if a.get("parent_name") and b.get("parent_name")
        else 0
    )
    same_dob = bool(a.get("dob") and str(a["dob"]) == str(b.get("dob")))
    score = 0.75 * n + 0.20 * (100 if same_dob else 0) + 0.05 * p
    return score, n >= 90 and guard and score >= 87 and (same_dob or p >= 90)


CATALOGUE = {
    "DATA_SCIENTIST": dict(
        PYTHON=18, SQL=16, STATISTICS=14, PANDAS=14, DATA_VISUALIZATION=12, MACHINE_LEARNING=16, MODEL_DEPLOYMENT=10
    ),
    "FULL_STACK_DEVELOPER": dict(
        HTML_CSS=12, JAVASCRIPT=18, TYPESCRIPT=12, REACT=18, API_DESIGN=16, SQL=14, TESTING=10
    ),
    "ML_ENGINEER": dict(
        PYTHON=18, MACHINE_LEARNING=20, STATISTICS=12, DATA_PIPELINES=15, MODEL_DEPLOYMENT=20, TESTING=15
    ),
    "CLOUD_ENGINEER": dict(LINUX=18, NETWORKING=18, CLOUD_FUNDAMENTALS=20, CONTAINERS=16, IAC=16, OBSERVABILITY=12),
}


def career(role, skills):
    weights = CATALOGUE[role]
    matched: list[dict[str, Any]] = [
        {"code": k, "label": k.replace("_", " ").title(), "weight": w, "evidence": skills[k]}
        for k, w in weights.items()
        if k in skills
    ]
    missing_inputs: list[dict[str, Any]] = [
        {"code": k, "label": k.replace("_", " ").title(), "weight": w} for k, w in weights.items() if k not in skills
    ]
    missing = sorted(missing_inputs, key=lambda x: (-x["weight"], x["code"]))
    score = sum(s["weight"] for s in matched)
    return dict(
        role_code=role,
        readiness_percent=score,
        matched_skills=matched,
        missing_skills=missing,
        recommended_steps=[
            dict(
                priority=i + 1,
                action=f"Study {s['label']}, build a measured project, then deploy and document it.",
                estimated_weeks=6,
                reason=f"{s['label']} contributes {s['weight']} missing points.",
            )
            for i, s in enumerate(missing)
        ],
        suggested_courses=[
            dict(title=s["label"] + " Foundations", provider="Generic learning resource", url=None) for s in missing
        ],
        explanation=f"Your evidenced skills cover {score} of 100 role-weight points. Self-reported skills add no points.",
        phrasing_source="RULE_BASED",
        catalogue_version=1,
    )


def trust(inputs):
    weights = load_weights("trust")
    thresholds = load_weights("fraud")["thresholds"]
    local = (
        0
        if inputs.get("missing_mandatory")
        else max(
            0,
            weights["local"]
            - weights["local_error_penalty"] * inputs.get("errors", 0)
            - weights["local_warning_penalty"] * inputs.get("warnings", 0),
        )
    )
    risk = inputs.get("risk", 0)
    values = [
        (
            "completeness",
            Decimal(str(weights["completeness"])) / 10 * inputs.get("complete_fields", 0),
            weights["completeness"],
        ),
        ("local", local, weights["local"]),
        (
            "certificates",
            min(weights["certificates"], weights["certificate_points_each"] * inputs.get("certificates", 0)),
            weights["certificates"],
        ),
        (
            "fraud",
            0
            if risk >= thresholds["high"]
            else weights["fraud_medium"]
            if risk >= thresholds["medium"]
            else weights["fraud"],
            weights["fraud"],
        ),
        ("review", weights["review"] if inputs.get("approved") else 0, weights["review"]),
        ("external", 0, weights["external"]),
    ]
    components = [
        dict(
            key=k,
            earned=float(v),
            max=m,
            reason={"external": "No official verification; mock contributes zero."}.get(
                k, f"Computed from {k} inputs."
            ),
            raw_inputs=inputs,
        )
        for k, v, m in values
    ]
    return dict(
        score=int(money_round(sum(Decimal(str(v)) for _, v, _ in values), "1")),
        maximum=100,
        components=components,
        formula_version=1,
        officially_verified=False,
    )


def certificate_confidence(extracted, student, as_of):
    n, guard = name_match(extracted.get("name"), student.get("full_name"))
    issuer = normalized_name(extracted.get("issuer"))
    providers = {"shiksham demo academy": r"SDA-[0-9]{8}", "synthetic cloud institute": r"SCI-[A-Z]{3}-[0-9]{5}"}
    i = Decimal(1) if issuer in providers else Decimal(".5") if issuer else Decimal(0)
    d = Decimal(0)
    try:
        issued = date.fromisoformat(extracted.get("date") or "")
        dob = date.fromisoformat(str(student["dob"]))
        d = Decimal(int(date(dob.year + 14, dob.month, min(dob.day, 28)) <= issued <= date.fromisoformat(as_of)))
    except (ValueError, TypeError, KeyError):
        pass
    credential = (extracted.get("credential_id") or "").upper()
    c = (
        Decimal(1)
        if issuer in providers and re.fullmatch(providers[issuer], credential)
        else Decimal(2) / Decimal(3)
        if re.fullmatch(r"[A-Z0-9-]{6,40}", credential)
        else Decimal(0)
    )
    confidence = money_round(
        100 * (Decimal(".5") * Decimal(str(n / 100)) + Decimal(".2") * i + Decimal(".15") * d + Decimal(".15") * c)
    )
    return float(confidence), dict(name=n / 100, issuer=float(i), date=float(d), credential_id=float(c)), guard

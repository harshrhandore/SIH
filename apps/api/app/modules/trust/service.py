"""Trust input policy and deterministic scoring, with zero official credit."""

from app.core.clock import utc_stamp

from decimal import Decimal
from app.core.weights import load_weights
from app.core.identifiers import valid_id
from app.core.numbers import money_round
from app.modules.trust import repository


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


def trust_for(conn, student):
    fraud_config = load_weights("fraud")
    sid = student["id"]
    terms, skills, findings, certs, approved = repository.inputs(conn, student)
    accepted = []
    seen_shas = set()
    seen_credentials = set()
    for c in certs:
        if (
            c["acceptance_status"] != "ACCEPTED"
            or c["verdict"] != "VERIFIED_LOCAL"
            or c["confidence"] < fraud_config["minimum_confidence"]
            or c["risk_score"] >= fraud_config["thresholds"]["medium"]
        ):
            continue
        credential = ((c.get("issuer") or "").strip().casefold(), (c.get("credential_id") or "").strip().casefold())
        if c["file_sha256"] in seen_shas or all(credential) and credential in seen_credentials:
            continue
        accepted.append(c)
        seen_shas.add(c["file_sha256"])
        if all(credential):
            seen_credentials.add(credential)
    fields = [
        valid_id(student["apaar_id"]),
        student["enrollment_no"],
        student["full_name"],
        student["dob"],
        student["program_id"],
        student["admission_year"],
        student["current_year"],
        student["email"],
        terms,
        skills,
    ]
    result = trust(
        dict(
            complete_fields=sum(bool(x) for x in fields),
            errors=len({f["check_code"] for f in findings if f["severity"] == "ERROR"}),
            warnings=len({f["check_code"] for f in findings if f["severity"] == "WARNING"}),
            missing_mandatory=any(f["check_code"] == "MISSING_MANDATORY" for f in findings),
            certificates=len(accepted),
            approved=bool(approved),
            risk=max([c["risk_score"] or 0 for c in certs if c["reviewed_at"] is None] + [0]),
        )
    )
    result.update(student_version=student["version_no"], computed_at=utc_stamp())
    repository.persist(conn, sid, result)
    return result

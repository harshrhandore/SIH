from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from psycopg.types.json import Jsonb
from app.db.session import one, many
from app.core.algorithms import trust, valid_id
from app.core.weights import load_weights


def jsonable(value):
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value


def epoch(conn, institution):
    return one(
        conn,
        "UPDATE institution_epochs SET data_epoch=data_epoch+1,updated_at=now() WHERE institution_id=%s RETURNING data_epoch",
        (institution,),
    )["data_epoch"]


def trust_for(conn, student):
    fraud_config = load_weights("fraud")
    sid = student["id"]
    terms = many(conn, "SELECT term_no FROM academic_performance WHERE student_id=%s", (sid,))
    skills = evidenced_skills(conn, sid)
    findings = many(
        conn,
        "SELECT check_code,severity FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
        (sid,),
    )
    certs = many(
        conn,
        "SELECT c.*,v.verdict,v.confidence,v.risk_score FROM certificates c LEFT JOIN LATERAL (SELECT * FROM certificate_verifications WHERE certificate_id=c.id ORDER BY created_at DESC,id DESC LIMIT 1) v ON true WHERE c.student_id=%s AND c.purpose='PASSPORT'",
        (sid,),
    )
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
    approved = one(
        conn,
        "SELECT 1 FROM review_cases c JOIN review_decisions d ON d.case_id=c.id WHERE c.student_id=%s AND c.status='APPROVED' AND d.action='APPROVE' AND (SELECT max(version_no) FROM record_versions WHERE student_id=%s AND created_at<=d.created_at)=%s AND NOT EXISTS(SELECT 1 FROM review_cases WHERE student_id=%s AND status<>'APPROVED') LIMIT 1",
        (sid, sid, student["version_no"], sid),
    )
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
    result.update(student_version=student["version_no"], computed_at=str(datetime.now().astimezone()))
    conn.execute(
        "INSERT INTO trust_scores(student_id,score,components) VALUES (%s,%s,%s) ON CONFLICT(student_id) DO UPDATE SET score=EXCLUDED.score,components=EXCLUDED.components,computed_at=now()",
        (sid, result["score"], Jsonb(result)),
    )
    return result


def evidenced_skills(conn, sid):
    rows = many(
        conn,
        "SELECT sk.code,sk.label,ss.* FROM student_skills ss JOIN skills sk ON sk.id=ss.skill_id WHERE ss.student_id=%s AND ss.proficiency>=2",
        (sid,),
    )
    result = {}
    for row in rows:
        table = {"PROJECT": "projects", "CERTIFICATE": "certificates", "INTERNSHIP": "internships"}.get(
            row["evidence_kind"]
        )
        if not table:
            continue
        evidence = one(conn, f"SELECT * FROM {table} WHERE id=%s AND student_id=%s", (row["evidence_id"], sid))
        if evidence and (table != "certificates" or evidence["acceptance_status"] == "ACCEPTED"):
            result[row["code"]] = [
                dict(
                    kind=row["evidence_kind"],
                    id=str(evidence["id"]),
                    title=evidence.get("title") or evidence.get("organization"),
                )
            ]
    return result


def passport(conn, student):
    sid = student["id"]
    result = dict(
        profile={
            k: student.get(k)
            for k in [
                "id",
                "full_name",
                "apaar_id",
                "institution_id",
                "institution_name",
                "program",
                "branch",
                "current_year",
                "admission_year",
                "data_quality_status",
                "external_status",
                "version_no",
                "total_terms",
                "term_type",
            ]
        },
        dob=student["dob"],
        email=student["email"],
        officially_verified=False,
    )
    result["terms"] = many(
        conn,
        "SELECT term_no,term_type,academic_year,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
        (sid,),
    )
    result["cgpa"] = result["terms"][-1]["cgpa"] if result["terms"] else None
    for table in ["projects", "internships", "achievements", "scholarships"]:
        result[table] = many(conn, f"SELECT * FROM {table} WHERE student_id=%s ORDER BY id", (sid,))
    result["certificates"] = many(
        conn,
        "SELECT id,title,issuer,issued_on,credential_id,purpose,acceptance_status FROM certificates WHERE student_id=%s ORDER BY created_at",
        (sid,),
    )
    result["skills"] = many(
        conn,
        "SELECT sk.code,sk.label,s.proficiency,s.evidence_kind,s.evidence_id FROM student_skills s JOIN skills sk ON sk.id=s.skill_id WHERE student_id=%s",
        (sid,),
    )
    result["trust"] = trust_for(conn, student)
    result["latest_case"] = one(
        conn, "SELECT * FROM review_cases WHERE student_id=%s ORDER BY created_at DESC LIMIT 1", (sid,)
    )
    return result


def dashboard(conn, institution):
    result = one(
        conn,
        "SELECT count(*)::int AS total,count(*) FILTER(WHERE data_quality_status='PASSED_LOCAL_CHECKS')::int AS clean,count(*) FILTER(WHERE data_quality_status='FLAGGED_FOR_REVIEW')::int AS flagged,count(*) FILTER(WHERE data_quality_status='INCOMPLETE')::int AS incomplete FROM students WHERE institution_id=%s",
        (institution,),
    )
    inst = one(conn, "SELECT expected_records,name FROM institutions WHERE id=%s", (institution,))
    result["institution_name"] = inst["name"]
    result["submission_percent"] = round(min(100, 100 * result["total"] / inst["expected_records"]), 2)
    result["missing_records"] = max(0, inst["expected_records"] - result["total"])
    result.update(
        one(
            conn,
            "SELECT count(*) FILTER(WHERE c.status<>'APPROVED')::int AS pending_reviews,count(*) FILTER(WHERE c.status='CORRECTION_REQUESTED')::int AS pending_corrections FROM review_cases c JOIN students s ON s.id=c.student_id WHERE s.institution_id=%s",
            (institution,),
        )
    )
    result["recent_imports"] = many(
        conn,
        "SELECT id,filename,status,total_rows,clean_rows,flagged_rows,incomplete_rows,created_at FROM import_batches WHERE institution_id=%s ORDER BY created_at DESC LIMIT 5",
        (institution,),
    )
    result["data_epoch"] = one(
        conn, "SELECT data_epoch FROM institution_epochs WHERE institution_id=%s", (institution,)
    )["data_epoch"]
    return result

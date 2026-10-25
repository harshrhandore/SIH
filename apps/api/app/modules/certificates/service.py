from app.modules.certificates.fraud import evaluate as evaluate
from app.modules.certificates.ocr import extract_text as extract_text
from app.modules.certificates.extract import inspect_document as inspect_document, fields_from_text as fields_from_text
from datetime import datetime
import hashlib
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.core.files import contained, root_path
from app.core.audit import append
from app.db.session import one
from app.settings import ROOT, settings


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
        cid = uid("certificate", filename)
        key = f"{student['institution_id']}/{student['id']}/{cid}.pdf"
        path = contained(root_path(settings.storage_root), key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        conn.execute(
            "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,acceptance_status,created_by) VALUES (%s,%s,%s,%s,%s,'application/pdf','PASSPORT','ACCEPTED',%s)",
            (cid, student["id"], title, key, sha, uid("user", "operator_a")),
        )
        certificate = one(conn, "SELECT * FROM certificates WHERE id=%s", (cid,))
        persist_report(
            conn, certificate, student, evaluate(data, "application/pdf", student), uuid4(), uid("user", "operator_a")
        )
    from app.modules.students.service import trust_for

    trust_for(conn, student)

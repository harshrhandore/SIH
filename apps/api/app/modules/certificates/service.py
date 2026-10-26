from app.modules.certificates import repository
from app.modules.certificates.fraud import evaluate as evaluate
from app.modules.certificates.ocr import extract_text as extract_text
from app.modules.certificates.extract import inspect_document as inspect_document, fields_from_text as fields_from_text
from datetime import datetime
import hashlib
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.core.files import contained, root_path
from app.core.audit import append
from app.settings import ROOT, settings
from app.core.http import idem
from datetime import timedelta, timezone
from uuid import UUID
from fastapi import Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.db.session import connect
from app.core.errors import fail
from app.core.security import allow, student_scope, reason
from app.core.rate_limit import limit
from app.core.files import store, read
from app.modules.students.service import trust_for, epoch
from app.modules.certificates import service as certificates
from app.modules.certificates.schemas import VerifyAlias
from app.modules.certificates.schemas import Acceptance


def persist_report(conn, certificate, student, result, key, actor):
    vid = uuid4()
    repository.persist_report_certificate_verifications(
        conn,
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
    repository.persist_report_certificates(
        conn, (result["extracted"]["issuer"], result["extracted"]["credential_id"], certificate["id"])
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

    student = repository.seed_certificates_students(conn, (uid("student", 1),))
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
        repository.seed_certificates_certificates(
            conn, (cid, student["id"], title, key, sha, uid("user", "operator_a"))
        )
        certificate = repository.seed_certificates_certificates_2(conn, (cid,))
        persist_report(
            conn, certificate, student, evaluate(data, "application/pdf", student), uuid4(), uid("user", "operator_a")
        )
    from app.modules.students.service import trust_for

    trust_for(conn, student)


def upload_certificate(
    student_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("TRIAL"),
    title: str = Form("Synthetic certificate"),
    user=None,
):
    allow(user, "OPERATOR", "OFFICER", "STUDENT")
    if purpose not in {"PASSPORT", "TRIAL"}:
        fail("INVALID_PURPOSE")
    data = file.file.read(10 * 1024 * 1024 + 1)
    mime, suffix = certificates.inspect_document(data)
    sha = hashlib.sha256(data).hexdigest()
    with connect() as conn:
        student = student_scope(conn, user, student_id, request)

        def work(key):
            existing = repository.work_certificates(conn, (student_id, sha, purpose))
            if existing:
                return dict(
                    certificate_id=existing["id"],
                    purpose=purpose,
                    file_sha256=sha,
                    status="PENDING",
                    duplicate_of=existing["id"],
                )
            storage, _ = store(data, student["institution_id"], student_id, suffix)
            cid = uuid4()
            repository.work_certificates_2(conn, (cid, student_id, title, storage, sha, mime, purpose, user["id"]))
            append(
                conn,
                student["institution_id"],
                user["id"],
                "CERTIFICATE_UPLOADED",
                "certificate",
                cid,
                "Uploaded synthetic certificate for local checks.",
                dict(purpose=purpose),
                student_id,
            )
            epoch(conn, student["institution_id"])
            return dict(certificate_id=cid, purpose=purpose, file_sha256=sha, status="PENDING", duplicate_of=None)

        return idem(conn, user, request, dict(sha=sha, purpose=purpose, title=title), work)


def verify_certificate(certificate_id: UUID, request: Request, user=None):
    from app.core.verification_lock import verification_slot

    with verification_slot():
        return verify_certificate_locked(certificate_id, request, user)


def verify_certificate_locked(certificate_id, request, user):
    allow(user, "OPERATOR", "OFFICER", "STUDENT")
    limit(("certificate", str(user["id"])), 20)
    try:
        key = UUID(request.headers.get("idempotency-key", ""))
    except ValueError:
        fail("IDEMPOTENCY_KEY_REQUIRED")
    with connect() as conn:
        certificate = repository.verify_certificate_locked_certificates(conn, (certificate_id,))
        if not certificate:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, certificate["student_id"], request)
        old = repository.verify_certificate_locked_certificate_verifications(conn, (certificate_id, key))
        if old:
            return report_response(old, certificate)
        if certificate["processing_status"] == "PROCESSING" and certificate["processing_started_at"] > datetime.now(
            timezone.utc
        ) - timedelta(seconds=120):
            fail("VERIFICATION_RUNNING", 409)
        repository.verify_certificate_locked_certificates_2(conn, (certificate_id,))
        data = read(certificate["storage_key"]).read_bytes()
        reuse = []
        if repository.verify_certificate_locked_certificates_3(conn, (certificate["file_sha256"], student["id"])):
            reuse.append(("SHA_REUSE_OTHER_STUDENT", 60))
    result = certificates.evaluate(data, certificate["mime_type"], student, reuse, actor=user["id"])
    with connect() as conn:
        student_scope(conn, user, student["id"], request)
        extracted = result["extracted"]
        if (
            extracted["issuer"]
            and extracted["credential_id"]
            and repository.verify_certificate_locked_certificates_4(
                conn, (extracted["issuer"], extracted["credential_id"], student["id"])
            )
        ):
            result = certificates.evaluate(
                data,
                certificate["mime_type"],
                student,
                reuse + [("CREDENTIAL_REUSE_OTHER_STUDENT", 65)],
                actor=user["id"],
            )
        current = repository.verify_certificate_locked_certificates_5(conn, (certificate_id,))
        prior = repository.verify_certificate_locked_certificate_verifications_2(conn, (certificate_id, key))
        if prior:
            return report_response(prior, current)
        fresh = student_scope(conn, user, student["id"], request)
        if fresh["version_no"] != student["version_no"]:
            repository.verify_certificate_locked_certificates_6(conn, (certificate_id,))
            fail("VERSION_CONFLICT", 409)
        response = certificates.persist_report(conn, certificate, student, result, key, user["id"])
        trust_for(conn, student)
        epoch(conn, student["institution_id"])
        return response


def report_response(row, certificate):
    return {
        **row["reasons"],
        "verification_id": row["id"],
        "certificate_id": certificate["id"],
        "purpose": certificate["purpose"],
        "trust_effect": "EXCLUDED_TRIAL" if certificate["purpose"] == "TRIAL" else "PASSPORT_EVIDENCE",
        "created_at": row["created_at"],
    }


def report(verification_id: UUID, request: Request, user=None):
    with connect() as conn:
        row = repository.report_certificate_verifications(conn, (verification_id,))
        if not row:
            fail("NOT_FOUND", 404)
        cert = repository.report_certificates(conn, (row["certificate_id"],))
        student_scope(conn, user, cert["student_id"], request)
        return report_response(row, cert)


def fraud(verification_id: UUID, request: Request, user=None):
    result = report(verification_id, request, user)
    return dict(
        verification_id=verification_id,
        risk=result["risk"]["level"],
        score=result["risk"]["score"],
        reasons=result["risk"]["reasons"],
        limitations=["Heuristic, not validated on real certificates."],
        not_assessed=result["not_assessed"],
    )


def certificate_file(certificate_id: UUID, request: Request, user=None):
    with connect() as conn:
        cert = repository.certificate_file_certificates(conn, (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student_scope(conn, user, cert["student_id"], request)
        return FileResponse(
            read(cert["storage_key"]),
            media_type=cert["mime_type"],
            filename="synthetic-certificate." + cert["storage_key"].split(".")[-1],
        )


def acceptance(certificate_id: UUID, body: Acceptance, request: Request, user=None):
    allow(user, "OPERATOR", "OFFICER")
    reason(body.reason)
    with connect() as conn:
        cert = repository.acceptance_certificates(conn, (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, cert["student_id"], request)
        if cert["purpose"] == "TRIAL":
            fail("TRIAL_CANNOT_ATTACH", 409)
        latest = repository.acceptance_certificate_verifications(conn, (certificate_id,))
        if body.action == "ACCEPT" and (
            not latest or latest["verdict"] != "VERIFIED_LOCAL" or latest["risk_score"] >= 30
        ):
            fail("LOCAL_REPORT_REQUIRED", 409)
        if body.action not in {"ACCEPT", "REJECT"}:
            fail("INVALID_ACTION")
        repository.acceptance_certificates_2(
            conn, ("ACCEPTED" if body.action == "ACCEPT" else "REJECTED", user["id"], body.reason, certificate_id)
        )
        append(
            conn,
            student["institution_id"],
            user["id"],
            "CERTIFICATE_REVIEWED",
            "certificate",
            certificate_id,
            body.reason,
            dict(action=body.action),
            student["id"],
        )
        return dict(
            certificate_id=certificate_id,
            acceptance_status="ACCEPTED" if body.action == "ACCEPT" else "REJECTED",
            trust_score=trust_for(conn, student)["score"],
            data_epoch=epoch(conn, student["institution_id"]),
        )


def verify_alias(body: VerifyAlias, request: Request, user=None):
    return verify_certificate(body.certificate_id, request, user)

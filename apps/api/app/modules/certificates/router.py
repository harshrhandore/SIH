"""Certificates HTTP operations."""

from app.core.http import idem
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import Request, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.db.session import connect, one
from app.core.errors import fail
from app.core.security import authenticated, allow, student_scope, reason
from app.core.rate_limit import limit
from app.core.files import store, read
from app.core.audit import append
from app.modules.students.service import trust_for, epoch
from app.modules.certificates import service as certificates
from app.modules.certificates.schemas import VerifyAlias
from app.modules.certificates.schemas import Acceptance
from fastapi import APIRouter

router = APIRouter(tags=["certificates"])


@router.post("/students/{student_id}/certificates", status_code=201)
def upload_certificate(
    student_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("TRIAL"),
    title: str = Form("Synthetic certificate"),
    user=Depends(authenticated),
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
            existing = one(
                conn,
                "SELECT id FROM certificates WHERE student_id=%s AND file_sha256=%s AND purpose=%s",
                (student_id, sha, purpose),
            )
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
            conn.execute(
                "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, student_id, title, storage, sha, mime, purpose, user["id"]),
            )
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


@router.post("/certificates/{certificate_id}/verify")
def verify_certificate(certificate_id: UUID, request: Request, user=Depends(authenticated)):
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
        certificate = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        if not certificate:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, certificate["student_id"], request)
        old = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s",
            (certificate_id, key),
        )
        if old:
            return report_response(old, certificate)
        if certificate["processing_status"] == "PROCESSING" and certificate["processing_started_at"] > datetime.now(
            timezone.utc
        ) - timedelta(seconds=120):
            fail("VERIFICATION_RUNNING", 409)
        conn.execute(
            "UPDATE certificates SET processing_status='PROCESSING',processing_started_at=now() WHERE id=%s",
            (certificate_id,),
        )
        data = read(certificate["storage_key"]).read_bytes()
        reuse = []
        if one(
            conn,
            "SELECT 1 FROM certificates WHERE file_sha256=%s AND student_id<>%s LIMIT 1",
            (certificate["file_sha256"], student["id"]),
        ):
            reuse.append(("SHA_REUSE_OTHER_STUDENT", 60))
    result = certificates.evaluate(data, certificate["mime_type"], student, reuse, actor=user["id"])
    with connect() as conn:
        student_scope(conn, user, student["id"], request)
        extracted = result["extracted"]
        if (
            extracted["issuer"]
            and extracted["credential_id"]
            and one(
                conn,
                "SELECT 1 FROM certificates WHERE lower(issuer)=lower(%s) AND lower(credential_id)=lower(%s) AND student_id<>%s LIMIT 1",
                (extracted["issuer"], extracted["credential_id"], student["id"]),
            )
        ):
            result = certificates.evaluate(
                data,
                certificate["mime_type"],
                student,
                reuse + [("CREDENTIAL_REUSE_OTHER_STUDENT", 65)],
                actor=user["id"],
            )
        current = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        prior = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s",
            (certificate_id, key),
        )
        if prior:
            return report_response(prior, current)
        fresh = student_scope(conn, user, student["id"], request)
        if fresh["version_no"] != student["version_no"]:
            conn.execute("UPDATE certificates SET processing_status='FAILED' WHERE id=%s", (certificate_id,))
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


@router.get("/certificate-verifications/{verification_id}")
def report(verification_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        row = one(conn, "SELECT * FROM certificate_verifications WHERE id=%s", (verification_id,))
        if not row:
            fail("NOT_FOUND", 404)
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s", (row["certificate_id"],))
        student_scope(conn, user, cert["student_id"], request)
        return report_response(row, cert)


@router.get("/certificate-verifications/{verification_id}/fraud")
def fraud(verification_id: UUID, request: Request, user=Depends(authenticated)):
    result = report(verification_id, request, user)
    return dict(
        verification_id=verification_id,
        risk=result["risk"]["level"],
        score=result["risk"]["score"],
        reasons=result["risk"]["reasons"],
        limitations=["Heuristic, not validated on real certificates."],
        not_assessed=result["not_assessed"],
    )


@router.get("/certificates/{certificate_id}/file")
def certificate_file(certificate_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s", (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student_scope(conn, user, cert["student_id"], request)
        return FileResponse(
            read(cert["storage_key"]),
            media_type=cert["mime_type"],
            filename="synthetic-certificate." + cert["storage_key"].split(".")[-1],
        )


@router.post("/certificates/{certificate_id}/acceptance")
def acceptance(certificate_id: UUID, body: Acceptance, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER")
    reason(body.reason)
    with connect() as conn:
        cert = one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", (certificate_id,))
        if not cert:
            fail("NOT_FOUND", 404)
        student = student_scope(conn, user, cert["student_id"], request)
        if cert["purpose"] == "TRIAL":
            fail("TRIAL_CANNOT_ATTACH", 409)
        latest = one(
            conn,
            "SELECT * FROM certificate_verifications WHERE certificate_id=%s ORDER BY created_at DESC LIMIT 1",
            (certificate_id,),
        )
        if body.action == "ACCEPT" and (
            not latest or latest["verdict"] != "VERIFIED_LOCAL" or latest["risk_score"] >= 30
        ):
            fail("LOCAL_REPORT_REQUIRED", 409)
        if body.action not in {"ACCEPT", "REJECT"}:
            fail("INVALID_ACTION")
        conn.execute(
            "UPDATE certificates SET acceptance_status=%s,reviewed_at=now(),reviewed_by=%s,resolution_reason=%s WHERE id=%s",
            ("ACCEPTED" if body.action == "ACCEPT" else "REJECTED", user["id"], body.reason, certificate_id),
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


@router.post("/verify")
def verify_alias(body: VerifyAlias, request: Request, user=Depends(authenticated)):
    return verify_certificate(body.certificate_id, request, user)

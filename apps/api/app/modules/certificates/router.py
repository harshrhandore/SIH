from uuid import UUID
from fastapi import Request, Depends, UploadFile, File, Form
from app.core.security import authenticated
from app.modules.certificates.schemas import VerifyAlias
from app.modules.certificates.schemas import Acceptance
from fastapi import APIRouter
from app.modules.certificates import service

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
    return service.upload_certificate(
        student_id=student_id, request=request, file=file, purpose=purpose, title=title, user=user
    )


@router.post("/certificates/{certificate_id}/verify")
def verify_certificate(certificate_id: UUID, request: Request, user=Depends(authenticated)):
    return service.verify_certificate(certificate_id=certificate_id, request=request, user=user)


@router.get("/certificate-verifications/{verification_id}")
def report(verification_id: UUID, request: Request, user=Depends(authenticated)):
    return service.report(verification_id=verification_id, request=request, user=user)


@router.get("/certificate-verifications/{verification_id}/fraud")
def fraud(verification_id: UUID, request: Request, user=Depends(authenticated)):
    return service.fraud(verification_id=verification_id, request=request, user=user)


@router.get("/certificates/{certificate_id}/file")
def certificate_file(certificate_id: UUID, request: Request, user=Depends(authenticated)):
    return service.certificate_file(certificate_id=certificate_id, request=request, user=user)


@router.post("/certificates/{certificate_id}/acceptance")
def acceptance(certificate_id: UUID, body: Acceptance, request: Request, user=Depends(authenticated)):
    return service.acceptance(certificate_id=certificate_id, body=body, request=request, user=user)


@router.post("/verify")
def verify_alias(body: VerifyAlias, request: Request, user=Depends(authenticated)):
    return service.verify_alias(body=body, request=request, user=user)

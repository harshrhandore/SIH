from uuid import UUID
from fastapi import Request, Depends
from app.core.security import authenticated
from app.core.contracts import Reason
from app.modules.verification.schemas import Version
from fastapi import APIRouter
from app.modules.verification import service

router = APIRouter(tags=["verification"])


@router.post("/students/{student_id}/checks")
def checks(student_id: UUID, body: Version, request: Request, user=Depends(authenticated)):
    return service.checks(student_id=student_id, body=body, request=request, user=user)


@router.post("/students/{student_id}/external-check")
def external_check(student_id: UUID, body: Reason, request: Request, user=Depends(authenticated)):
    return service.external_check(student_id=student_id, body=body, request=request, user=user)

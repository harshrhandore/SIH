"""Typed audit HTTP contracts; policy and transactions live in the service."""

from uuid import UUID
from fastapi import APIRouter, Request, Depends
from app.core.security import authenticated
from app.modules.audit import service
from app.modules.audit.schemas import TimelineResponse, ChainVerification, EventsResponse

router = APIRouter(tags=["audit"])


@router.get("/students/{student_id}/timeline", response_model=TimelineResponse)
def timeline(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    return service.student_timeline(student_id, request, page, page_size, user)


@router.get("/audit/verify-chain", response_model=ChainVerification, response_model_exclude_unset=True)
def verify_chain(institution_id: UUID, user=Depends(authenticated)):
    return service.chain_summary(institution_id, user)


@router.get("/audit/events", response_model=EventsResponse, response_model_exclude_none=True)
def audit_events(
    request: Request,
    institution_id: UUID | None = None,
    case_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    return service.events(request, institution_id, case_id, page, page_size, user)

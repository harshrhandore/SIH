from uuid import UUID
from fastapi import Request, Depends
from app.core.security import authenticated
from app.core.contracts import Reason
from app.modules.reviews.schemas import Decision
from app.modules.reviews.schemas import CandidateDecision
from fastapi import APIRouter
from app.modules.reviews import service

router = APIRouter(tags=["reviews"])


@router.get("/cases")
def list_cases(
    status: str | None = None,
    institution_id: UUID | None = None,
    rule: str | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    return service.list_cases(
        status=status, institution_id=institution_id, rule=rule, q=q, page=page, page_size=page_size, user=user
    )


@router.get("/cases/{case_id}")
def case_detail(case_id: UUID, request: Request, user=Depends(authenticated)):
    return service.case_detail(case_id=case_id, request=request, user=user)


@router.post("/cases/{case_id}/access")
def case_access(case_id: UUID, body: Reason, user=Depends(authenticated)):
    return service.case_access(case_id=case_id, body=body, user=user)


@router.post("/cases/{case_id}/decisions")
def decide(case_id: UUID, body: Decision, request: Request, user=Depends(authenticated)):
    return service.decide(case_id=case_id, body=body, request=request, user=user)


@router.post("/duplicate-candidates/{candidate_id}/decision")
def candidate_decision(candidate_id: UUID, body: CandidateDecision, request: Request, user=Depends(authenticated)):
    return service.candidate_decision(candidate_id=candidate_id, body=body, request=request, user=user)

"""Career routes with scoped, deterministic service responses."""

from uuid import UUID
from fastapi import APIRouter, Depends, Request
from app.core.security import authenticated, allow
from app.modules.career import service
from app.modules.career.catalogue import CATALOGUE
from app.modules.career.schemas import Career, CareerResponse, HistoryResponse, RolesResponse

router = APIRouter(tags=["career"])


@router.get("/career/roles", response_model=RolesResponse)
def career_roles(user=Depends(authenticated)):
    allow(user, "STUDENT", "OPERATOR", "OFFICER")
    return dict(
        catalogue_version=1,
        roles=[
            dict(code=k, label=k.replace("_", " ").title(), skills=[dict(code=c, weight=w) for c, w in weights.items()])
            for k, weights in CATALOGUE.items()
        ],
    )


@router.post("/students/{student_id}/career", response_model=CareerResponse)
def ask_career(student_id: UUID, body: Career, request: Request, user=Depends(authenticated)):
    return service.ask(student_id, body, request, user)


@router.get("/students/{student_id}/career/history", response_model=HistoryResponse)
def career_history(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    return service.history(student_id, request, page, page_size, user)

from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.security import authenticated
from app.modules.institutions import service
from app.modules.institutions.schemas import InstitutionsResponse, ProgramsResponse

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=InstitutionsResponse)
def institutions(state: str | None = None, user=Depends(authenticated)):
    return service.institutions(user, state)


@router.get("/{institution_id}/programs", response_model=ProgramsResponse)
def programs(institution_id: UUID, user=Depends(authenticated)):
    return service.programs(user, institution_id)

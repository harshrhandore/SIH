from uuid import UUID
from fastapi import Request, Depends
from app.core.security import authenticated
from app.schemas import SearchResponse
from app.modules.students.schemas import Patch
from fastapi import APIRouter
from app.modules.students import service

router = APIRouter(tags=["students"])


@router.get("/dashboard")
def get_dashboard(institution_id: UUID | None = None, user=Depends(authenticated)):
    return service.get_dashboard(institution_id=institution_id, user=user)


@router.get("/students/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str = "",
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    branch: str | None = None,
    current_year: int | None = None,
    quality: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "name",
    user=Depends(authenticated),
):
    return service.search(
        request=request,
        q=q,
        institution_id=institution_id,
        program_id=program_id,
        branch=branch,
        current_year=current_year,
        quality=quality,
        page=page,
        page_size=page_size,
        sort=sort,
        user=user,
    )


@router.get("/students/{student_id}")
def student(student_id: UUID, request: Request, include_evidence: bool = True, user=Depends(authenticated)):
    return service.student(student_id=student_id, request=request, user=user, include_evidence=include_evidence)


@router.get("/students/{student_id}/evidence/{section}")
def student_evidence(student_id: UUID, section: str, request: Request, user=Depends(authenticated)):
    return service.student_evidence(student_id, section, request, user)


@router.get("/student/{apaar_id}")
def student_by_id(apaar_id: str, request: Request, user=Depends(authenticated)):
    return service.student_by_id(apaar_id=apaar_id, request=request, user=user)


@router.get("/students/{student_id}/versions")
def versions(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    return service.versions(student_id=student_id, request=request, page=page, page_size=page_size, user=user)


@router.patch("/students/{student_id}")
def patch_student(student_id: UUID, body: Patch, request: Request, user=Depends(authenticated)):
    return service.patch_student(student_id=student_id, body=body, request=request, user=user)

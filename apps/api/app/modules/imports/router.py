from uuid import UUID
from fastapi import Request, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.security import authenticated
from app.core.contracts import Reason
from app.modules.imports.schemas import Mapping
from app.modules.imports.schemas import Confirm
from fastapi import APIRouter
from app.modules.imports import service

router = APIRouter(tags=["imports"])


@router.post("/imports", status_code=201)
def upload_import(
    request: Request, file: UploadFile = File(...), institution_id: UUID = Form(...), user=Depends(authenticated)
):
    return service.upload_import(request=request, file=file, institution_id=institution_id, user=user)


@router.get("/imports")
def list_imports(page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    return service.list_imports(page=page, page_size=page_size, user=user)


@router.get("/imports/{batch_id}")
def import_detail(batch_id: UUID, user=Depends(authenticated)):
    return service.import_detail(batch_id=batch_id, user=user)


@router.put("/imports/{batch_id}/mapping")
def set_mapping(batch_id: UUID, body: Mapping, user=Depends(authenticated)):
    return service.set_mapping(batch_id=batch_id, body=body, user=user)


@router.post("/imports/{batch_id}/validate", status_code=202)
def validate_import(
    batch_id: UUID, body: Confirm, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)
):
    return service.validate_import(batch_id=batch_id, body=body, request=request, tasks=tasks, user=user)


@router.get("/import-jobs/{job_id}")
def get_job(job_id: UUID, user=Depends(authenticated)):
    return service.get_job(job_id=job_id, user=user)


@router.post("/import-jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: UUID, body: Reason, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)):
    return service.retry_job(job_id=job_id, body=body, request=request, tasks=tasks, user=user)


@router.get("/imports/{batch_id}/report")
def import_report(batch_id: UUID, user=Depends(authenticated)):
    return service.import_report(batch_id=batch_id, user=user)


@router.get("/imports/{batch_id}/errors.csv")
def errors_csv(batch_id: UUID, user=Depends(authenticated)):
    return service.errors_csv(batch_id=batch_id, user=user)

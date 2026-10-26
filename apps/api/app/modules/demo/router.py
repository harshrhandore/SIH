from uuid import UUID
from fastapi import Request, Depends, BackgroundTasks
from app.core.security import authenticated
from app.modules.demo.schemas import SessionControls
from app.modules.demo.schemas import BenchmarkRequest
from fastapi import APIRouter
from app.modules.demo import service

router = APIRouter(tags=["demo"])


@router.get("/demo/config")
def demo_config(user=Depends(authenticated)):
    return service.demo_config(user=user)


@router.get("/demo/manifest")
def demo_manifest(user=Depends(authenticated)):
    return service.demo_manifest(user=user)


@router.get("/demo/fixtures/{fixture_key}")
def fixture(fixture_key: str, user=Depends(authenticated)):
    return service.fixture(fixture_key=fixture_key, user=user)


@router.get("/demo/audit-sandbox")
@router.get("/demo/audit-sandbox/verify")
def sandbox_status(institution_id: UUID, user=Depends(authenticated)):
    return service.sandbox_status(institution_id=institution_id, user=user)


@router.put("/demo/session-controls")
def session_controls(body: SessionControls, user=Depends(authenticated)):
    return service.session_controls(body=body, user=user)


@router.get("/demo/performance")
def performance(user=Depends(authenticated)):
    return service.performance(user=user)


@router.post("/demo/benchmarks", status_code=202)
def web_benchmark(body: BenchmarkRequest, request: Request, tasks: BackgroundTasks, user=Depends(authenticated)):
    return service.web_benchmark(body=body, request=request, tasks=tasks, user=user)


@router.get("/demo/benchmarks/{run_id}")
def benchmark_result(run_id: UUID, user=Depends(authenticated)):
    return service.benchmark_result(run_id=run_id, user=user)

from uuid import UUID
from fastapi import Depends, BackgroundTasks
from app.core.security import authenticated
from fastapi import APIRouter
from app.modules.analytics import service
from app.modules.analytics.schemas import AnalyticsResponse, OversightResponse, RefreshStatus, RefreshQueued

router = APIRouter(tags=["analytics"])


@router.get("/oversight", response_model=OversightResponse)
def oversight(
    state: str | None = None,
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    return service.oversight(
        state=state, institution_id=institution_id, program_id=program_id, page=page, page_size=page_size, user=user
    )


@router.post("/analytics/refresh", status_code=202, response_model=RefreshQueued)
def refresh_analytics(tasks: BackgroundTasks, user=Depends(authenticated)):
    return service.refresh_analytics(tasks=tasks, user=user)


@router.get("/analytics/refresh-status", response_model=RefreshStatus)
def refresh_status(user=Depends(authenticated)):
    return service.refresh_status(user=user)


analytics_data = service.analytics_data
for kind in ["admissions", "placements", "performance", "data-quality"]:

    def make_endpoint(selected):

        def endpoint(
            institution_id: UUID | None = None,
            program_id: UUID | None = None,
            year: int | None = None,
            state: str | None = None,
            user=Depends(authenticated),
        ):
            return analytics_data(selected, user, institution_id, program_id, year, state)

        endpoint.__name__ = "analytics_" + selected.replace("-", "_")
        return endpoint

    router.add_api_route("/analytics/" + kind, make_endpoint(kind), methods=["GET"], response_model=AnalyticsResponse)

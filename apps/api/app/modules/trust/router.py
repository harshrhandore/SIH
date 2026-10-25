"""Trust HTTP operations."""

from uuid import UUID
from fastapi import Request, Depends
from app.db.session import connect
from app.core.security import authenticated, student_scope
from app.modules.trust.service import trust_for
from fastapi import APIRouter
from app.modules.trust.schemas import TrustResponse

router = APIRouter(tags=["trust"])


@router.get("/students/{student_id}/trust", response_model=TrustResponse)
def student_trust(student_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        return trust_for(conn, student_scope(conn, user, student_id, request))

"""HTTP authentication boundary; credentials never enter request logs."""

from fastapi import APIRouter, Depends, Request
from app.core.errors import fail
from app.core.rate_limit import limit
from app.core.security import authenticated
from app.settings import settings
from app.schemas import UserResponse
from app.modules.auth import service
from app.modules.auth.schemas import Login, Refresh, Logout, TokenResponse, LogoutResponse, DemoAccountsResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/demo-accounts", response_model=DemoAccountsResponse)
def accounts():
    if not settings.demo_mode:
        fail("NOT_FOUND", 404)
    return dict(
        accounts=[
            dict(key=k, email=e, label=label, role=r)
            for k, e, label, r in [
                ("operator_a", "operator.a@example.test", "College Operator — Institution A", "OPERATOR"),
                ("operator_b", "operator.b@example.test", "College Operator — Institution B", "OPERATOR"),
                ("officer", "officer@example.test", "Verification Officer", "OFFICER"),
                ("admin", "admin@example.test", "AICTE Administrator", "ADMIN"),
                ("student", "student.riya@example.test", "Student — Riya Sharma", "STUDENT"),
            ]
        ],
        password_required=True,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: Login, request: Request):
    limit(("login", body.email.strip().casefold(), request.client.host if request.client else "unknown"))
    return service.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: Refresh, request: Request):
    return service.refresh(body.refresh_token, request.headers.get("x-csrf-token", ""))


@router.post("/logout", response_model=LogoutResponse)
def logout(body: Logout, user=Depends(authenticated)):
    return service.logout(user, body.all_sessions)


@router.get("/me", response_model=UserResponse)
def me(user=Depends(authenticated)):
    return service.current_user(user)

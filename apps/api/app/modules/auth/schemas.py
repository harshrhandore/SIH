"""Authentication request and public response contracts."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas import UserResponse


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Strict):
    email: str = Field(max_length=254)
    password: str = Field(description="At most 72 UTF-8 bytes; enforced before bcrypt.")


class Refresh(Strict):
    refresh_token: str = Field(min_length=1, max_length=512)


class Logout(Strict):
    all_sessions: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    csrf_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: UserResponse


class LogoutResponse(BaseModel):
    logged_out: Literal[True]


class DemoAccount(BaseModel):
    key: str
    email: str
    label: str
    role: Literal["OPERATOR", "OFFICER", "ADMIN", "STUDENT"]


class DemoAccountsResponse(BaseModel):
    accounts: list[DemoAccount]
    password_required: Literal[True]

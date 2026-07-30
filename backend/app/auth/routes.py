"""Login/logout/status for the shared-password gate. No accounts: everyone who knows
the one configured password gets the same session cookie."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth.service import COOKIE_NAME, issue_session_token, verify_password, verify_session_token
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class LoginRequest(BaseModel):
    password: str


class AuthStatus(BaseModel):
    required: bool
    authenticated: bool


@router.get("/status", response_model=AuthStatus)
def get_status(request: Request) -> AuthStatus:
    if settings.app_password is None:
        return AuthStatus(required=False, authenticated=True)
    token = request.cookies.get(COOKIE_NAME)
    authenticated = bool(token and verify_session_token(token, settings.app_password))
    return AuthStatus(required=True, authenticated=authenticated)


@router.post("/login", response_model=AuthStatus)
def login(body: LoginRequest, response: Response) -> AuthStatus:
    if settings.app_password is None:
        return AuthStatus(required=False, authenticated=True)
    if not verify_password(body.password, settings.app_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")
    token = issue_session_token(settings.app_password)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return AuthStatus(required=True, authenticated=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)

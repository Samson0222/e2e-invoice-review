"""Route protection for the shared-password gate. A no-op whenever APP_PASSWORD is
unset, so local development never needs it configured."""

from fastapi import HTTPException, Request, status

from app.auth.service import COOKIE_NAME, verify_session_token
from app.config import settings


def require_auth(request: Request) -> None:
    if settings.app_password is None:
        return
    token = request.cookies.get(COOKIE_NAME)
    if not token or not verify_session_token(token, settings.app_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required.")

"""A stateless, single-shared-password session: no accounts, no server-side session
store. The cookie is a timestamp plus an HMAC over that timestamp, keyed off the
configured app password, so a valid cookie can only have been issued by someone who
knew the password at the time it was signed."""

import hashlib
import hmac
import time

COOKIE_NAME = "session"
_SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60


def _signing_key(password: str) -> bytes:
    return hashlib.sha256(password.encode()).digest()


def issue_session_token(password: str) -> str:
    expires_at = int(time.time()) + _SESSION_LIFETIME_SECONDS
    signature = hmac.new(_signing_key(password), str(expires_at).encode(), hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"


def verify_session_token(token: str, password: str) -> bool:
    expires_at_raw, _, signature = token.partition(".")
    if not expires_at_raw or not signature:
        return False
    try:
        expires_at = int(expires_at_raw)
    except ValueError:
        return False
    if expires_at < int(time.time()):
        return False
    expected = hmac.new(_signing_key(password), expires_at_raw.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_password(candidate: str, password: str) -> bool:
    return hmac.compare_digest(candidate, password)

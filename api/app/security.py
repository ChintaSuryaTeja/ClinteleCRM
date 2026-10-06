"""Password hashing and login tokens (JWT)."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import settings

ALGORITHM = "HS256"

# Argon2, a slow-on-purpose hash, so stolen hashes are expensive to crack.
_hasher = PasswordHash.recommended()

# Used when a login email doesn't exist, so the response takes as long as a
# wrong password. Otherwise timing would reveal which emails have accounts.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    # The token holds only the user id. Organization and role are read from the
    # database on every request, so a role change takes effect immediately.
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def read_access_token(token: str) -> int | None:
    """Return the user id in a valid token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None

"""Reusable FastAPI dependencies: database session, current user, role checks.

Endpoints declare what they need in their signature, for example
`def list_users(admin: AdminUser, db: DbSession)`, and FastAPI runs these
functions first. If one raises an HTTPException, the endpoint never runs.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import read_access_token

SESSION_COOKIE = "crm_session"

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_access_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can do this")
    return user


AdminUser = Annotated[User, Depends(require_admin)]

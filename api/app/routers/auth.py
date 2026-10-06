"""Signup, login, logout and "who am I".

After signup or login the API puts the token in an httpOnly cookie. JavaScript
running in the page cannot read httpOnly cookies, so a script-injection bug
cannot steal the token. SameSite=Lax stops other websites from sending the
cookie along with a POST to this API.
"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.deps import SESSION_COOKIE, CurrentUser, DbSession
from app.models import Organization, Role, User
from app.schemas import LoginIn, MeOut, SignupIn
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_access_token(user.id),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, response: Response, db: DbSession) -> MeOut:
    """Create a new organization with the caller as its first admin."""
    organization = Organization(name=body.organization_name.strip())
    user = User(
        organization=organization,
        email=body.email,
        password_hash=hash_password(body.password),
        role=Role.ADMIN,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None

    set_session_cookie(response, user)
    return MeOut.model_validate(user)


@router.post("/login")
def login(body: LoginIn, response: Response, db: DbSession) -> MeOut:
    user = db.scalar(select(User).where(User.email == body.email))
    if not verify_password(body.password, user.password_hash if user else None):
        # Same message whether the email or the password was wrong.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    set_session_cookie(response, user)
    return MeOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")


@router.get("/me")
def me(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user)

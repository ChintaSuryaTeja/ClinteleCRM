"""User management inside one organization (admins only).

The organization always comes from the logged-in admin, never from the request,
so an admin cannot list or create users in someone else's organization.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AdminUser, DbSession
from app.models import User
from app.schemas import UserCreateIn, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(admin: AdminUser, db: DbSession) -> list[UserOut]:
    users = db.scalars(
        select(User)
        .where(User.organization_id == admin.organization_id)
        .order_by(User.created_at, User.id)
    )
    return [UserOut.model_validate(user) for user in users]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, admin: AdminUser, db: DbSession) -> UserOut:
    """Add a user to the admin's organization with a temporary password."""
    user = User(
        organization_id=admin.organization_id,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None
    return UserOut.model_validate(user)

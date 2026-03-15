"""Users router -- user management endpoints.

User registration (POST /users/) has been removed. Users are created via
Auth Service and provisioned as shadow users on first JWT encounter.
Password reset has also been removed as passwords are managed by Auth Service.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.api.v1.schemas import UsersResponse
from langflow.services.auth.utils import get_current_active_superuser
from langflow.services.database.models.user.crud import get_user_by_id, update_user
from langflow.services.database.models.user.model import User, UserRead, UserUpdate

router = APIRouter(tags=["Users"], prefix="/users")


@router.get("/whoami", response_model=UserRead)
async def read_current_user(
    current_user: CurrentActiveUser,
) -> User:
    """Retrieve the current user's data."""
    return current_user


@router.get("/", dependencies=[Depends(get_current_active_superuser)])
async def read_all_users(
    *,
    skip: int = 0,
    limit: int = 10,
    session: DbSession,
) -> UsersResponse:
    """Retrieve a list of users from the database with pagination."""
    query: SelectOfScalar = select(User).offset(skip).limit(limit)
    users = (await session.exec(query)).fetchall()

    count_query = select(func.count()).select_from(User)
    total_count = (await session.exec(count_query)).first()

    return UsersResponse(
        total_count=total_count,
        users=[UserRead(**user.model_dump()) for user in users],
    )


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: UUID,
    user_update: UserUpdate,
    user: CurrentActiveUser,
    session: DbSession,
) -> User:
    """Update an existing user's data.

    Note: Password changes are handled by Auth Service, not Langflow.
    """
    # Prevent users from deactivating their own account to avoid lockout
    if user.id == user_id and user_update.is_active is False:
        raise HTTPException(status_code=403, detail="You can't deactivate your own user account")

    if not user.is_superuser and user_update.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")

    if not user.is_superuser and user.id != user_id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Password changes are not supported -- Auth Service manages passwords
    if user_update.password:
        raise HTTPException(
            status_code=400,
            detail="Password changes are handled by Auth Service, not Langflow.",
        )

    if user_db := await get_user_by_id(session, user_id):
        user_update.password = user_db.password
        return await update_user(user_db, user_update, session)
    raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    session: DbSession,
) -> dict:
    """Delete a user from the database."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You can't delete your own user account")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")

    stmt = select(User).where(User.id == user_id)
    user_db = (await session.exec(stmt)).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    await session.delete(user_db)
    return {"detail": "User deleted"}

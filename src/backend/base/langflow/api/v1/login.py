"""Login router -- session check and logout only.

Legacy login/auto_login/refresh endpoints have been removed.
All authentication flows through the Auth Service.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from langflow.api.utils import DbSession
from langflow.services.database.models.user.model import UserRead
from langflow.services.deps import get_auth_service, get_settings_service

router = APIRouter(tags=["Login"])


class SessionResponse(BaseModel):
    """Session validation response."""

    authenticated: bool
    user: UserRead | None = None
    store_api_key: str | None = None


@router.get("/session", include_in_schema=False)
async def get_session(
    request: Request,
    db: DbSession,
) -> SessionResponse:
    """Validate session and return user information.

    This endpoint checks if the user is authenticated via cookie or Authorization header.
    It does not raise an error if unauthenticated, allowing the frontend to gracefully
    handle the session state.
    """
    from langflow.services.auth.utils import oauth2_login

    # Try to get the token from the request (cookie or Authorization header)
    try:
        token = await oauth2_login(request)
        if not token:
            return SessionResponse(authenticated=False)

        # Validate the token and get user
        user = await get_auth_service().get_current_user_from_access_token(token, db)
        if not user or not user.is_active:
            return SessionResponse(authenticated=False)

        return SessionResponse(
            authenticated=True,
            user=UserRead.model_validate(user, from_attributes=True),
        )
    except Exception:  # noqa: BLE001
        # Any authentication error means not authenticated
        return SessionResponse(authenticated=False)


@router.post("/logout", include_in_schema=False)
async def logout(response: Response):
    auth_settings = get_settings_service().auth_settings

    response.delete_cookie(
        "refresh_token_lf",
        httponly=auth_settings.REFRESH_HTTPONLY,
        samesite=auth_settings.REFRESH_SAME_SITE,
        secure=auth_settings.REFRESH_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
    )
    response.delete_cookie(
        "access_token_lf",
        httponly=auth_settings.ACCESS_HTTPONLY,
        samesite=auth_settings.ACCESS_SAME_SITE,
        secure=auth_settings.ACCESS_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
    )
    response.delete_cookie(
        "apikey_tkn_lflw",
        httponly=auth_settings.ACCESS_HTTPONLY,
        samesite=auth_settings.ACCESS_SAME_SITE,
        secure=auth_settings.ACCESS_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
    )
    return {"message": "Logout successful"}

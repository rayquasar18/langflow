"""Auth utility functions and FastAPI dependencies.

All authentication delegates to the active auth service (QuasarAuthService).
Legacy password/token helper functions have been removed.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Annotated

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, Security, WebSocket, WebSocketException, status
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from lfx.services.deps import injectable_session_scope

from langflow.services.auth.exceptions import (
    AuthenticationError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    MissingCredentialsError,
)
from langflow.services.deps import get_auth_service

if TYPE_CHECKING:
    from lfx.services.settings.service import SettingsService
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.user.model import User, UserRead


class OAuth2PasswordBearerCookie(OAuth2PasswordBearer):
    """Custom OAuth2 scheme that checks Authorization header first, then cookies.

    This allows the application to work with HttpOnly cookies while supporting
    explicit Authorization headers for backward compatibility and testing scenarios.
    If an explicit Authorization header is provided, it takes precedence over cookies.
    """

    async def __call__(self, request: Request) -> str | None:
        # First, check for explicit Authorization header (for backward compatibility and testing)
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer" and param:
            return param

        # Fall back to cookie (for HttpOnly cookie support in browser-based clients)
        token = request.cookies.get("access_token_lf")
        if token:
            return token

        # If auto_error is True, this would raise an exception
        # Since we set auto_error=False, return None
        return None


oauth2_login = OAuth2PasswordBearerCookie(tokenUrl="api/v1/login", auto_error=False)

API_KEY_NAME = "x-api-key"

api_key_query = APIKeyQuery(name=API_KEY_NAME, scheme_name="API key query", auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_NAME, scheme_name="API key header", auto_error=False)


def _auth_service():
    """Return the currently configured auth service.

    This is an internal helper to keep imports local to the auth services layer.
    **New code should prefer calling `get_auth_service()` directly** instead of
    using this helper or adding new thin wrapper functions here.
    """
    return get_auth_service()


async def api_key_security(
    query_param: Annotated[str | None, Security(api_key_query)],
    header_param: Annotated[str | None, Security(api_key_header)],
) -> UserRead | None:
    return await _auth_service().api_key_security(query_param, header_param)


async def ws_api_key_security(api_key: str | None) -> UserRead:
    return await _auth_service().ws_api_key_security(api_key)


def _auth_error_to_http(e: AuthenticationError) -> HTTPException:
    """Map auth exceptions to 401 Unauthorized or 403 Forbidden.

    Langflow returns 403 for missing/invalid credentials; 401 for invalid/expired tokens.
    """
    if isinstance(
        e,
        (MissingCredentialsError, InvalidCredentialsError, InsufficientPermissionsError),
    ):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


def _populate_request_state(request: Request) -> None:
    """Populate request.state with JWT claims from the _current_claims context var.

    Called after auth service validates a JWT (sets _current_claims).
    This makes tenant_id, user_id, role, tier, and is_platform_admin
    available to all route handlers and downstream middleware via request.state.
    """
    from langflow.services.auth.quasar_service import _current_claims

    claims = _current_claims.get()
    if claims:
        request.state.tenant_id = claims.get("tenant_id")
        request.state.user_id = claims.get("sub")
        request.state.role = claims.get("role")
        request.state.tier = claims.get("tier")
        request.state.is_platform_admin = claims.get("is_platform_admin", False)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Security(oauth2_login)],
    query_param: Annotated[str | None, Security(api_key_query)],
    header_param: Annotated[str | None, Security(api_key_header)],
    db: AsyncSession = Depends(injectable_session_scope),
) -> User:
    try:
        user = await _auth_service().get_current_user(token, query_param, header_param, db)
    except AuthenticationError as e:
        raise _auth_error_to_http(e) from e
    else:
        # Populate request.state from JWT claims context var
        _populate_request_state(request)
        return user


async def get_current_user_from_access_token(
    token: str | None,
    db: AsyncSession,
) -> User:
    """Compatibility helper to resolve a user from an access token.

    This simply delegates to the active auth service's
    `get_current_user_from_access_token` implementation.

    **For new code, prefer calling
    `get_auth_service().get_current_user_from_access_token(...)` directly**
    instead of importing this function.
    """
    try:
        return await _auth_service().get_current_user_from_access_token(token, db)
    except AuthenticationError as e:
        raise _auth_error_to_http(e) from e


WS_AUTH_REASON = "Missing or invalid credentials (cookie, token or API key)."


async def get_current_user_for_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> User | UserRead:
    """Extracts credentials from WebSocket and delegates to auth service."""
    token = websocket.cookies.get("access_token_lf") or websocket.query_params.get("token")
    api_key = (
        websocket.query_params.get("x-api-key")
        or websocket.query_params.get("api_key")
        or websocket.headers.get("x-api-key")
        or websocket.headers.get("api_key")
    )

    try:
        return await _auth_service().get_current_user_for_websocket(token, api_key, db)
    except AuthenticationError as e:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=WS_AUTH_REASON) from e


async def get_current_user_for_sse(
    request: Request,
    db: AsyncSession = Depends(injectable_session_scope),
) -> User | UserRead:
    """Extracts credentials from request and delegates to auth service.

    Accepts cookie (access_token_lf) or API key (x-api-key query param).
    """
    token = request.cookies.get("access_token_lf")
    api_key = request.query_params.get("x-api-key") or request.headers.get("x-api-key")

    try:
        user = await _auth_service().get_current_user_for_sse(token, api_key, db)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid credentials (cookie or API key).",
        ) from e
    else:
        _populate_request_state(request)
        return user


async def get_optional_user(
    token: Annotated[str | None, Security(oauth2_login)],
    query_param: Annotated[str | None, Security(api_key_query)],
    header_param: Annotated[str | None, Security(api_key_header)],
    db: AsyncSession = Depends(injectable_session_scope),
) -> User | None:
    """Get the current user if authenticated, otherwise return None.

    This is useful for endpoints that need to behave differently for authenticated
    vs unauthenticated users (e.g., returning different response types).

    Returns:
        User | None: The authenticated user if valid credentials are provided, None otherwise.
    """
    try:
        user = await _auth_service().get_current_user(token, query_param, header_param, db)
    except (AuthenticationError, HTTPException):
        return None
    else:
        if user and user.is_active:
            return user
        return None


async def get_webhook_user(flow_id: str, request: Request) -> UserRead:
    """Get the user for webhook execution.

    When WEBHOOK_AUTH_ENABLE=false, allows execution as the flow owner without API key.
    When WEBHOOK_AUTH_ENABLE=true, requires API key authentication and validates flow ownership.

    Args:
        flow_id: The ID of the flow being executed
        request: The FastAPI request object

    Returns:
        UserRead: The user to execute the webhook as

    Raises:
        HTTPException: If authentication fails or user doesn't have permission
    """
    return await _auth_service().get_webhook_user(flow_id, request)


async def get_current_active_user(user: User = Depends(get_current_user)) -> User | UserRead:
    result = await _auth_service().get_current_active_user(user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return result


async def get_current_active_superuser(user: User = Depends(get_current_user)) -> User | UserRead:
    result = await _auth_service().get_current_active_superuser(user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return result


def get_fernet(settings_service: SettingsService) -> Fernet:
    """Get a Fernet instance for encryption/decryption.

    Args:
        settings_service: Settings service to get the secret key

    Returns:
        Fernet instance for encryption/decryption
    """
    import random

    secret_key: str = settings_service.auth_settings.SECRET_KEY.get_secret_value()

    # Replicate the original _ensure_valid_key logic from AuthService
    MINIMUM_KEY_LENGTH = 32  # noqa: N806
    if len(secret_key) < MINIMUM_KEY_LENGTH:
        # Generate deterministic key from seed for short keys
        random.seed(secret_key)
        key = bytes(random.getrandbits(8) for _ in range(32))
        key = base64.urlsafe_b64encode(key)
    else:
        # Add padding for longer keys
        padding_needed = 4 - len(secret_key) % 4
        padded_key = secret_key + "=" * padding_needed
        key = padded_key.encode()

    return Fernet(key)


def encrypt_api_key(api_key: str, settings_service: SettingsService | None = None) -> str:  # noqa: ARG001
    return _auth_service().encrypt_api_key(api_key)


def decrypt_api_key(
    encrypted_api_key: str,
    settings_service: SettingsService | None = None,  # noqa: ARG001
    fernet_obj=None,  # noqa: ARG001
) -> str:
    return _auth_service().decrypt_api_key(encrypted_api_key)


async def get_current_user_mcp(
    token: Annotated[str | None, Security(oauth2_login)],
    query_param: Annotated[str | None, Security(api_key_query)],
    header_param: Annotated[str | None, Security(api_key_header)],
    db: AsyncSession = Depends(injectable_session_scope),
) -> User:
    try:
        return await _auth_service().get_current_user_mcp(token, query_param, header_param, db)
    except AuthenticationError as e:
        raise _auth_error_to_http(e) from e


async def get_current_active_user_mcp(user: User = Depends(get_current_user_mcp)) -> User:
    return await _auth_service().get_current_active_user_mcp(user)

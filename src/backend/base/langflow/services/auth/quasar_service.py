"""Quasar Auth Service: validates Auth Service RS256 JWTs via JWKS endpoint.

This service replaces the built-in Langflow AuthService. It:
- Validates RS256 JWTs issued by the Auth Service using PyJWKClient (JWKS)
- Provisions shadow user records on first JWT encounter (JIT provisioning)
- Preserves API key authentication for programmatic access
- Does NOT issue tokens -- all tokens come from the Auth Service
"""

from __future__ import annotations

import base64
import contextvars
import os
import random
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any
from uuid import UUID

import jwt
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request, WebSocketException, status
from jwt import InvalidTokenError as JWTInvalidTokenError
from jwt import PyJWKClient
from lfx.log.logger import logger
from lfx.services.auth.base import BaseAuthService

from langflow.services.auth.exceptions import (
    InactiveUserError,
    InvalidTokenError,
    MissingCredentialsError,
    TokenExpiredError,
)
from langflow.services.auth.exceptions import (
    InvalidTokenError as AuthInvalidTokenError,
)
from langflow.services.database.models.api_key.crud import check_key
from langflow.services.database.models.user.crud import get_user_by_id
from langflow.services.database.models.user.model import User, UserRead
from langflow.services.schema import ServiceType

if TYPE_CHECKING:
    from datetime import timedelta

    from lfx.services.settings.service import SettingsService
    from sqlmodel.ext.asyncio.session import AsyncSession


# ---------------------------------------------------------------------------
# Context variable for propagating JWT claims to middleware / downstream
# ---------------------------------------------------------------------------

_current_claims: contextvars.ContextVar[dict | None] = contextvars.ContextVar("_current_claims", default=None)

MINIMUM_KEY_LENGTH = 32
SHADOW_USER_PASSWORD = "!quasar-shadow-no-login"  # noqa: S105


class QuasarAuthService(BaseAuthService):
    """Auth service that validates Auth Service RS256 JWTs via JWKS endpoint.

    Replaces Langflow's built-in AuthService entirely. Langflow does not
    issue tokens -- all authentication flows through the Auth Service.
    """

    name = ServiceType.AUTH_SERVICE.value

    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service

        # JWKS client for RS256 public key verification
        jwks_url = os.environ.get("JWKS_URL", "http://auth:8000/.well-known/jwks.json")
        self.jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            lifespan=300,  # 5 minute cache
        )

        # Fernet for API key encryption (reuses existing logic)
        self._fernet = self._build_fernet(settings_service)

        self.set_ready()

    @property
    def settings(self) -> SettingsService:
        return self.settings_service

    # ------------------------------------------------------------------
    # Fernet key setup (same logic as old AuthService._ensure_valid_key)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_fernet(settings_service: SettingsService) -> Fernet:
        secret_key: str = settings_service.auth_settings.SECRET_KEY.get_secret_value()
        if len(secret_key) < MINIMUM_KEY_LENGTH:
            random.seed(secret_key)
            key = bytes(random.getrandbits(8) for _ in range(32))
            key = base64.urlsafe_b64encode(key)
        else:
            padding_needed = 4 - len(secret_key) % 4
            padded_key = secret_key + "=" * padding_needed
            key = padded_key.encode()
        return Fernet(key)

    # ------------------------------------------------------------------
    # JWT validation
    # ------------------------------------------------------------------

    async def _validate_token(self, token: str) -> dict:
        """Validate RS256 JWT using JWKS-fetched public key.

        Returns:
            Decoded claims dict on success.

        Raises:
            TokenExpiredError: Token has expired.
            InvalidTokenError: Token is invalid (wrong algo, bad sig, missing claims, wrong type).
        """
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"require": ["sub", "tenant_id", "role", "type", "exp"]},
            )
        except jwt.ExpiredSignatureError as e:
            msg = "Token has expired"
            raise TokenExpiredError(msg) from e
        except (JWTInvalidTokenError, jwt.DecodeError, Exception) as e:
            msg = "Invalid token"
            raise InvalidTokenError(msg) from e

        # Verify token type
        if payload.get("type") != "access":
            msg = "Not an access token"
            raise InvalidTokenError(msg)

        return payload

    # ------------------------------------------------------------------
    # Shadow user JIT provisioning
    # ------------------------------------------------------------------

    async def get_or_create_user_from_claims(self, claims: dict, db: Any) -> User:
        """Get or create a shadow user from Auth Service JWT claims.

        Shadow users exist solely for Langflow FK relationships. The Auth
        Service remains the source of truth for user data.
        """
        user_id = UUID(claims["sub"])
        user = await get_user_by_id(db, user_id)

        if user is None:
            user = User(
                id=user_id,
                username=claims.get("email", f"user-{user_id}"),
                password=SHADOW_USER_PASSWORD,
                is_active=True,
                is_superuser=claims.get("is_platform_admin", False),
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
        else:
            # Sync fields from claims on each encounter
            changed = False
            new_superuser = claims.get("is_platform_admin", False)
            if user.is_superuser != new_superuser:
                user.is_superuser = new_superuser
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                await db.flush()

        return user

    # ------------------------------------------------------------------
    # Core authentication: get_current_user
    # ------------------------------------------------------------------

    async def authenticate_with_credentials(
        self,
        token: str | None,
        api_key: str | None,
        db: AsyncSession,
    ) -> User | UserRead:
        """Authenticate with JWT token or API key."""
        if token:
            payload = await self._validate_token(token)
            user = await self.get_or_create_user_from_claims(payload, db)
            # Propagate claims via context var
            _current_claims.set(payload)
            if not user.is_active:
                msg = "User account is inactive"
                raise InactiveUserError(msg)
            return user

        if api_key:
            result = await check_key(db, api_key)
            if not result:
                msg = "Invalid API key"
                from langflow.services.auth.exceptions import InvalidCredentialsError

                raise InvalidCredentialsError(msg)
            if isinstance(result, User):
                user_read = UserRead.model_validate(result, from_attributes=True)
                if not user_read.is_active:
                    msg = "User account is inactive"
                    raise InactiveUserError(msg)
                return user_read
            msg = "Invalid API key result"
            from langflow.services.auth.exceptions import InvalidCredentialsError

            raise InvalidCredentialsError(msg)

        msg = "No authentication credentials provided"
        raise MissingCredentialsError(msg)

    async def get_current_user(
        self,
        token: str | Coroutine | None,
        query_param: str | None,
        header_param: str | None,
        db: AsyncSession,
    ) -> User | UserRead:
        """Get current user from JWT or API key."""
        # Resolve coroutine token if needed
        resolved_token: str | None = None
        if isinstance(token, Coroutine):
            resolved_token = await token
        elif isinstance(token, str):
            resolved_token = token

        api_key = query_param or header_param

        return await self.authenticate_with_credentials(resolved_token, api_key, db)

    async def get_current_user_from_access_token(
        self,
        token: str | Coroutine | None,
        db: AsyncSession,
    ) -> User:
        """Get user from access token only (no API key path)."""
        if token is None:
            msg = "Missing authentication token"
            raise MissingCredentialsError(msg)

        resolved_token: str
        if isinstance(token, Coroutine):
            resolved_token = await token
        elif isinstance(token, str):
            resolved_token = token
        else:
            msg = "Invalid token format"
            raise AuthInvalidTokenError(msg)

        payload = await self._validate_token(resolved_token)
        user = await self.get_or_create_user_from_claims(payload, db)
        _current_claims.set(payload)

        if not user.is_active:
            msg = "User account is inactive"
            raise InactiveUserError(msg)

        return user

    async def get_current_user_for_websocket(
        self,
        token: str | None,
        api_key: str | None,
        db: AsyncSession,
    ) -> User | UserRead:
        """Get current user for WebSocket connections."""
        return await self.authenticate_with_credentials(token, api_key, db)

    async def get_current_user_for_sse(
        self,
        token: str | None,
        api_key: str | None,
        db: AsyncSession,
    ) -> User | UserRead:
        """Get current user for SSE connections."""
        return await self.authenticate_with_credentials(token, api_key, db)

    # ------------------------------------------------------------------
    # User validation
    # ------------------------------------------------------------------

    async def get_current_active_user(self, current_user: User | UserRead) -> User | UserRead | None:
        if not current_user.is_active:
            return None
        return current_user

    async def get_current_active_superuser(self, current_user: User | UserRead) -> User | UserRead | None:
        if not current_user.is_active or not current_user.is_superuser:
            return None
        return current_user

    # ------------------------------------------------------------------
    # Username/password auth -- DISABLED (Auth Service handles login)
    # ------------------------------------------------------------------

    async def authenticate_user(self, username: str, password: str, db: AsyncSession) -> Any | None:
        msg = "Langflow login is disabled. Authenticate via Auth Service."
        raise NotImplementedError(msg)

    # ------------------------------------------------------------------
    # Token creation -- DISABLED (Langflow does not issue tokens)
    # ------------------------------------------------------------------

    async def create_user_tokens(
        self,
        user_id: UUID,
        db: AsyncSession,
        *,
        update_last_login: bool = False,
    ) -> dict:
        msg = "Langflow does not issue tokens. Use Auth Service."
        raise NotImplementedError(msg)

    async def create_refresh_token(self, refresh_token: str, db: AsyncSession) -> dict:
        msg = "Langflow does not issue tokens. Use Auth Service."
        raise NotImplementedError(msg)

    def create_token(self, data: dict, expires_delta: timedelta) -> str:
        msg = "Langflow does not create JWTs. Use Auth Service."
        raise NotImplementedError(msg)

    async def create_super_user(self, username: str, password: str, db: AsyncSession) -> Any:
        msg = "Langflow does not create users. Use Auth Service."
        raise NotImplementedError(msg)

    async def create_user_longterm_token(self, db: AsyncSession) -> tuple:
        msg = "Langflow does not issue tokens. Use Auth Service."
        raise NotImplementedError(msg)

    # ------------------------------------------------------------------
    # Token utility
    # ------------------------------------------------------------------

    def get_user_id_from_token(self, token: str) -> UUID:
        """Extract user ID from token without full validation (utility only)."""
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
            return UUID(claims["sub"])
        except (KeyError, JWTInvalidTokenError, ValueError):
            return UUID(int=0)

    # ------------------------------------------------------------------
    # API key authentication (preserved from old AuthService)
    # ------------------------------------------------------------------

    def create_user_api_key(self, user_id: UUID) -> dict:
        """Create an API key for a user.

        Note: This still creates a JWT-like key for backward compatibility.
        In future, this may be replaced with opaque API keys.
        """
        msg = "API key creation requires Auth Service integration."
        raise NotImplementedError(msg)

    async def api_key_security(
        self,
        query_param: str | None,
        header_param: str | None,
        db: AsyncSession | None = None,
    ) -> UserRead | None:
        """Validate API key from query or header parameters."""
        from langflow.services.deps import session_scope

        if not query_param and not header_param:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An API key must be passed as query or header",
            )

        api_key = query_param or header_param
        if api_key is None:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing API key",
            )

        if db is not None:
            return await self._check_api_key(api_key, db)

        async with session_scope() as new_db:
            return await self._check_api_key(api_key, new_db)

    async def _check_api_key(self, api_key: str, db: AsyncSession) -> UserRead:
        """Check API key and return user."""
        result = await check_key(db, api_key)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing API key",
            )
        if isinstance(result, User):
            return UserRead.model_validate(result, from_attributes=True)
        msg = "Invalid result type"
        raise ValueError(msg)

    async def ws_api_key_security(self, api_key: str | None) -> UserRead:
        """Validate API key for WebSocket connections."""
        from langflow.services.deps import session_scope

        if not api_key:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="An API key must be passed as query or header",
            )

        async with session_scope() as db:
            result = await check_key(db, api_key)
            if not result:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid or missing API key",
                )
            if isinstance(result, User):
                return UserRead.model_validate(result, from_attributes=True)

        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Authentication subsystem error",
        )

    # ------------------------------------------------------------------
    # Webhook user
    # ------------------------------------------------------------------

    async def get_webhook_user(self, flow_id: str, request: Request) -> UserRead:
        """Get user for webhook execution (preserves existing logic)."""
        from langflow.helpers.user import get_user_by_flow_id_or_endpoint_name
        from langflow.services.deps import session_scope

        settings_service = self.settings

        if not settings_service.auth_settings.WEBHOOK_AUTH_ENABLE:
            try:
                flow_owner = await get_user_by_flow_id_or_endpoint_name(flow_id)
                if flow_owner is None:
                    raise HTTPException(status_code=404, detail="Flow not found")
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=404, detail="Flow not found") from exc
            else:
                return flow_owner

        api_key_header_val = request.headers.get("x-api-key")
        api_key_query_val = request.query_params.get("x-api-key")

        if not api_key_header_val and not api_key_query_val:
            raise HTTPException(
                status_code=403,
                detail="API key required when webhook authentication is enabled",
            )

        api_key = api_key_header_val or api_key_query_val

        try:
            async with session_scope() as db:
                result = await check_key(db, api_key)
                if not result:
                    logger.warning("Invalid API key provided for webhook")
                    raise HTTPException(status_code=403, detail="Invalid API key")
                authenticated_user = UserRead.model_validate(result, from_attributes=True)
                logger.info("Webhook API key validated successfully")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Webhook API key validation error: {exc}")
            raise HTTPException(status_code=403, detail="API key authentication failed") from exc

        try:
            flow_owner = await get_user_by_flow_id_or_endpoint_name(flow_id)
            if flow_owner is None:
                raise HTTPException(status_code=404, detail="Flow not found")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Flow not found") from exc

        if flow_owner.id != authenticated_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only execute webhooks for flows you own",
            )

        return authenticated_user

    # ------------------------------------------------------------------
    # API key encryption (preserved from old AuthService)
    # ------------------------------------------------------------------

    def encrypt_api_key(self, api_key: str) -> str:
        encrypted_key = self._fernet.encrypt(api_key.encode())
        return encrypted_key.decode()

    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """Decrypt an encrypted API key."""
        if not isinstance(encrypted_api_key, str) or not encrypted_api_key:
            logger.debug("decrypt_api_key called with invalid input (empty or non-string)")
            return ""

        if not encrypted_api_key.startswith("gAAAAA"):
            return encrypted_api_key

        try:
            return self._fernet.decrypt(encrypted_api_key.encode()).decode()
        except Exception as primary_exception:  # noqa: BLE001
            logger.debug(
                "Decryption using UTF-8 encoded API key failed. Error: %s. "
                "Retrying decryption using the raw string input.",
                primary_exception,
            )
            try:
                return self._fernet.decrypt(encrypted_api_key).decode()
            except Exception as secondary_exception:  # noqa: BLE001
                logger.warning(
                    "API key decryption failed after retry. Primary error: %s, Secondary error: %s",
                    primary_exception,
                    secondary_exception,
                )
                return ""

    # ------------------------------------------------------------------
    # MCP auth (delegates to standard auth methods)
    # ------------------------------------------------------------------

    async def get_current_user_mcp(
        self,
        token: str | Coroutine | None,
        query_param: str | None,
        header_param: str | None,
        db: AsyncSession,
    ) -> User | UserRead:
        """Get current user for MCP endpoints."""
        return await self.get_current_user(token, query_param, header_param, db)

    async def get_current_active_user_mcp(self, current_user: User | UserRead) -> User | UserRead:
        """Validate MCP user is active."""
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
        return current_user

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    async def teardown(self) -> None:
        """Teardown the auth service (no-op)."""
        logger.debug("QuasarAuthService teardown")

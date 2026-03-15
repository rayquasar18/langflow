"""Tests for the Langflow auth service.

Tests for removed functionality (local login, token creation, password
management) are marked skip because QuasarAuthService delegates these
to the Auth Service. See test_quasar_auth.py for JWKS/JWT tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from langflow.services.auth.exceptions import (
    InvalidTokenError,
)
from langflow.services.auth.service import AuthService
from langflow.services.database.models.user.model import User
from lfx.services.settings.auth import AuthSettings
from pydantic import SecretStr

SKIP_REASON = "Removed: Langflow no longer issues tokens/manages passwords (Auth Service handles this)"


@pytest.fixture
def auth_settings(tmp_path) -> AuthSettings:
    settings = AuthSettings(CONFIG_DIR=str(tmp_path))
    settings.SECRET_KEY = SecretStr("unit-test-secret")
    settings.AUTO_LOGIN = False
    settings.WEBHOOK_AUTH_ENABLE = False
    settings.ACCESS_TOKEN_EXPIRE_SECONDS = 60
    settings.REFRESH_TOKEN_EXPIRE_SECONDS = 120
    return settings


@pytest.fixture
def auth_service(auth_settings, tmp_path) -> AuthService:
    settings_service = SimpleNamespace(
        auth_settings=auth_settings,
        settings=SimpleNamespace(config_dir=str(tmp_path)),
    )
    with patch("langflow.services.auth.quasar_service.PyJWKClient"):
        return AuthService(settings_service)


def _dummy_user(user_id: UUID, *, active: bool = True) -> User:
    return User(
        id=user_id,
        username="tester",
        password="hashed",  # noqa: S106 - test fixture data  # pragma: allowlist secret
        is_active=active,
        is_superuser=False,
    )


# =============================================================================
# Removed functionality -- skipped tests
# =============================================================================


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_get_current_user_from_access_token_returns_active_user(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_get_current_user_from_access_token_rejects_expired(
    auth_service: AuthService,
    auth_settings: AuthSettings,
):
    pass


@pytest.mark.anyio
async def test_get_current_user_from_access_token_rejects_malformed_token(auth_service: AuthService):
    """CT-010: Malformed Bearer token must raise InvalidTokenError; jwt.decode rejects invalid tokens."""
    db = AsyncMock()
    malformed_tokens = [
        "invalid.token.here",  # invalid signature / not a valid JWT
        "not-a-jwt",  # not 3 segments, jwt.decode raises
    ]
    for token in malformed_tokens:
        with pytest.raises(InvalidTokenError):
            await auth_service.get_current_user_from_access_token(token, db)


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_get_current_user_from_access_token_requires_active_user(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_refresh_token_requires_refresh_type(auth_service: AuthService):
    pass


def test_encrypt_and_decrypt_api_key_roundtrip(auth_service: AuthService):
    api_key = "super-secret-api-key"  # pragma: allowlist secret

    encrypted = auth_service.encrypt_api_key(api_key)
    assert encrypted != api_key

    decrypted = auth_service.decrypt_api_key(encrypted)
    assert decrypted == api_key


@pytest.mark.skip(reason=SKIP_REASON)
def test_password_helpers_roundtrip(auth_service: AuthService):
    pass


# =============================================================================
# Token Creation Tests -- all skipped (Langflow no longer issues tokens)
# =============================================================================


@pytest.mark.skip(reason=SKIP_REASON)
def test_create_token_contains_expected_claims(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
def test_get_user_id_from_token_valid(auth_service: AuthService):
    pass


def test_get_user_id_from_token_invalid_returns_zero_uuid(auth_service: AuthService):
    """Test that invalid token returns zero UUID."""
    result = auth_service.get_user_id_from_token("invalid-token")
    assert result == UUID(int=0)


@pytest.mark.skip(reason=SKIP_REASON)
def test_create_user_api_key(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_user_tokens(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_user_tokens_updates_last_login(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_refresh_token_valid(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_refresh_token_user_not_found(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_create_refresh_token_inactive_user(auth_service: AuthService):
    pass


# =============================================================================
# User Validation Tests (still relevant -- QuasarAuthService implements these)
# =============================================================================


@pytest.mark.anyio
async def test_get_current_active_user_active(auth_service: AuthService):
    """Test active user passes validation."""
    user = _dummy_user(uuid4(), active=True)
    result = await auth_service.get_current_active_user(user)
    assert result is user


@pytest.mark.anyio
async def test_get_current_active_user_inactive(auth_service: AuthService):
    """Test inactive user returns None."""
    user = _dummy_user(uuid4(), active=False)

    result = await auth_service.get_current_active_user(user)
    assert result is None


@pytest.mark.anyio
async def test_get_current_active_superuser_valid(auth_service: AuthService):
    """Test active superuser passes validation."""
    user = User(
        id=uuid4(),
        username="admin",
        password="hashed",  # noqa: S106 # pragma: allowlist secret
        is_active=True,
        is_superuser=True,
    )
    result = await auth_service.get_current_active_superuser(user)
    assert result is user


@pytest.mark.anyio
async def test_get_current_active_superuser_inactive(auth_service: AuthService):
    """Test inactive superuser returns None."""
    user = User(
        id=uuid4(),
        username="admin",
        password="hashed",  # noqa: S106 # pragma: allowlist secret
        is_active=False,
        is_superuser=True,
    )

    result = await auth_service.get_current_active_superuser(user)
    assert result is None


@pytest.mark.anyio
async def test_get_current_active_superuser_not_superuser(auth_service: AuthService):
    """Test non-superuser returns None."""
    user = _dummy_user(uuid4(), active=True)  # is_superuser=False by default

    result = await auth_service.get_current_active_superuser(user)
    assert result is None


# =============================================================================
# Authenticate User Tests -- all skipped
# =============================================================================


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_authenticate_user_success(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_authenticate_user_wrong_password(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_authenticate_user_not_found(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_authenticate_user_inactive_never_logged_in(auth_service: AuthService):
    pass


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.anyio
async def test_authenticate_user_inactive_previously_logged_in(auth_service: AuthService):
    pass


# =============================================================================
# MCP Authentication Tests (still relevant)
# =============================================================================


@pytest.mark.anyio
async def test_get_current_active_user_mcp_active(auth_service: AuthService):
    """Test MCP active user validation passes."""
    user = _dummy_user(uuid4(), active=True)
    result = await auth_service.get_current_active_user_mcp(user)
    assert result is user


@pytest.mark.anyio
async def test_get_current_active_user_mcp_inactive(auth_service: AuthService):
    """Test MCP inactive user validation fails."""
    user = _dummy_user(uuid4(), active=False)

    with pytest.raises(HTTPException) as exc:
        await auth_service.get_current_active_user_mcp(user)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

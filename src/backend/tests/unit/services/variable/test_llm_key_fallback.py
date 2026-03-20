"""Tests for LLM key fallback chain: personal > tenant > platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from langflow.services.deps import get_settings_service
from langflow.services.variable.constants import VARIABLE_TO_PROVIDER
from langflow.services.variable.service import DatabaseVariableService
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    settings_service = get_settings_service()
    return DatabaseVariableService(settings_service)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_llm_key_client_sentinels(monkeypatch):
    """Reset module-level cached env values between tests."""
    import langflow.services.variable.llm_key_client as mod

    monkeypatch.setattr(mod, "_AUTH_URL", None)
    monkeypatch.setattr(mod, "_SERVICE_KEY", None)
    monkeypatch.setenv("AUTH_INTERNAL_URL", "http://test-auth:8000")
    monkeypatch.setenv("INTERNAL_SERVICE_KEY", "test-service-key")  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# VARIABLE_TO_PROVIDER mapping tests
# ---------------------------------------------------------------------------


async def test_variable_to_provider_contains_openai():
    assert "OPENAI_API_KEY" in VARIABLE_TO_PROVIDER
    assert VARIABLE_TO_PROVIDER["OPENAI_API_KEY"] == "openai"  # pragma: allowlist secret


async def test_variable_to_provider_contains_anthropic():
    assert "ANTHROPIC_API_KEY" in VARIABLE_TO_PROVIDER  # pragma: allowlist secret
    assert VARIABLE_TO_PROVIDER["ANTHROPIC_API_KEY"] == "anthropic"  # pragma: allowlist secret


async def test_variable_to_provider_contains_google():
    assert "GOOGLE_API_KEY" in VARIABLE_TO_PROVIDER  # pragma: allowlist secret
    assert VARIABLE_TO_PROVIDER["GOOGLE_API_KEY"] == "google"  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# resolve_llm_key tests
# ---------------------------------------------------------------------------


async def test_resolve_llm_key_returns_key_on_200():
    """resolve_llm_key returns the key from response JSON on 200."""
    from langflow.services.variable.llm_key_client import resolve_llm_key

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"provider": "openai", "key": "sk-platform123"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await resolve_llm_key("openai", "tenant123")

    assert result == "sk-platform123"


async def test_resolve_llm_key_returns_none_on_404():
    """resolve_llm_key returns None when Auth Service responds 404."""
    from langflow.services.variable.llm_key_client import resolve_llm_key

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await resolve_llm_key("openai", "tenant123")

    assert result is None


async def test_resolve_llm_key_returns_none_on_timeout():
    """resolve_llm_key returns None when httpx raises TimeoutException (graceful degradation)."""
    from langflow.services.variable.llm_key_client import resolve_llm_key

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await resolve_llm_key("openai", "tenant123")

    assert result is None


async def test_resolve_llm_key_returns_none_on_connection_error():
    """resolve_llm_key returns None when Auth Service is unreachable."""
    from langflow.services.variable.llm_key_client import resolve_llm_key

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await resolve_llm_key("openai", "tenant123")

    assert result is None


# ---------------------------------------------------------------------------
# DatabaseVariableService.get_variable fallback tests
# ---------------------------------------------------------------------------


async def test_get_variable_returns_personal_key_when_exists(service, session: AsyncSession):
    """get_variable returns personal key when it exists in DB (existing behavior, unchanged)."""
    user_id = uuid4()
    await service.create_variable(user_id, "OPENAI_API_KEY", "sk-personal123", session=session)

    result = await service.get_variable(user_id, "OPENAI_API_KEY", "api_key", session, tenant_id="tenant123")

    assert result == "sk-personal123"


async def test_get_variable_falls_back_to_resolve_llm_key(service, session: AsyncSession):
    """get_variable falls back to resolve_llm_key when personal key not found."""
    user_id = uuid4()

    with patch(
        "langflow.services.variable.llm_key_client.resolve_llm_key",
        new_callable=AsyncMock,
        return_value="sk-tenant-key",
    ) as mock_resolve:
        result = await service.get_variable(user_id, "OPENAI_API_KEY", "api_key", session, tenant_id="tenant123")

    mock_resolve.assert_awaited_once_with(provider="openai", tenant_id="tenant123")
    assert result == "sk-tenant-key"


async def test_get_variable_falls_back_with_tenant_id(service, session: AsyncSession):
    """get_variable uses tenant_id parameter for resolve_llm_key."""
    user_id = uuid4()
    specific_tenant = "specific-tenant-456"

    with patch(
        "langflow.services.variable.llm_key_client.resolve_llm_key",
        new_callable=AsyncMock,
        return_value="sk-specific-tenant",
    ) as mock_resolve:
        result = await service.get_variable(user_id, "ANTHROPIC_API_KEY", "api_key", session, tenant_id=specific_tenant)

    mock_resolve.assert_awaited_once_with(provider="anthropic", tenant_id=specific_tenant)
    assert result == "sk-specific-tenant"


async def test_get_variable_raises_for_non_llm_variable(service, session: AsyncSession):
    """get_variable raises ValueError for non-LLM variable not in VARIABLE_TO_PROVIDER."""
    user_id = uuid4()

    with pytest.raises(ValueError, match=r"MY_CUSTOM_VAR variable not found\."):
        await service.get_variable(user_id, "MY_CUSTOM_VAR", "value", session, tenant_id="tenant123")

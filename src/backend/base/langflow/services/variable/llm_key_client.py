"""Async client to resolve tenant/platform LLM keys from Auth Service."""

from __future__ import annotations

import os

from lfx.log.logger import logger

_AUTH_URL: str | None = None
_SERVICE_KEY: str | None = None

_HTTP_OK = 200
_HTTP_NOT_FOUND = 404


def _get_auth_url() -> str:
    global _AUTH_URL  # noqa: PLW0603
    if _AUTH_URL is None:
        _AUTH_URL = os.environ.get("AUTH_INTERNAL_URL", "http://auth:8000")
    return _AUTH_URL


def _get_service_key() -> str:
    global _SERVICE_KEY  # noqa: PLW0603
    if _SERVICE_KEY is None:
        _SERVICE_KEY = os.environ.get("INTERNAL_SERVICE_KEY", "")
    return _SERVICE_KEY


async def resolve_llm_key(provider: str, tenant_id: str) -> str | None:
    """Call Auth Service to resolve the best tenant/platform key for a provider.

    Returns the decrypted key string, or None if no key is configured or
    the Auth Service is unreachable.
    """
    import httpx

    url = f"{_get_auth_url()}/api/v1/llm-keys/resolve"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                url,
                params={"provider": provider, "tenant_id": tenant_id},
                headers={"X-Service-Key": _get_service_key()},
            )
            if resp.status_code == _HTTP_OK:
                data = resp.json()
                return data.get("key")
            # 404 = no key configured, not an error
            if resp.status_code != _HTTP_NOT_FOUND:
                await logger.awarning(f"Auth Service /llm-keys/resolve returned {resp.status_code}")
    except httpx.TimeoutException:
        await logger.awarning("Auth Service /llm-keys/resolve timed out -- continuing without fallback key")
    except httpx.RequestError as exc:
        await logger.awarning(f"Auth Service /llm-keys/resolve unreachable: {exc} -- continuing without fallback key")
    return None

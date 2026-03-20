"""Admin proxy routes -- forwards admin API calls to Auth Service.

The Auth Service is internal-only (not reachable from the browser). The Langflow
frontend calls these /api/v1/admin/* proxy routes, and Langflow forwards them to
AUTH_INTERNAL_URL. The tenant flows route is the exception: it queries Langflow's
own DB since flows live here.

Proxy routes (forward JWT Authorization header):
    GET  /admin/stats                          -> Auth /api/v1/admin/stats
    GET  /admin/stats/{tenant_id}              -> Auth /api/v1/admin/stats/{tenant_id}
    GET  /admin/health                         -> Auth /api/v1/admin/health
    GET  /admin/tenants                        -> Auth /api/v1/tenants
    GET  /admin/tenants/{tenant_id}            -> Auth /api/v1/tenants/{tenant_id}
    PATCH /admin/tenants/{tenant_id}           -> Auth /api/v1/tenants/{tenant_id}
    POST /admin/tenants/{tenant_id}/suspend    -> Auth /api/v1/tenants/{tenant_id}/suspend
    POST /admin/tenants/{tenant_id}/reactivate -> Auth /api/v1/tenants/{tenant_id}/reactivate

Langflow-native route (queries Langflow DB):
    GET  /admin/tenants/{tenant_id}/flows      -> Langflow DB query
"""

from __future__ import annotations

import os
from http import HTTPStatus

import httpx
from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from langflow.services.database.models.flow.model import Flow
from langflow.services.deps import get_db_service

router = APIRouter(prefix="/admin", tags=["admin-proxy"])


class _Config:
    """Lazy-initialized config container to avoid module-level env reads."""

    _auth_url: str | None = None

    @classmethod
    def auth_url(cls) -> str:
        if cls._auth_url is None:
            cls._auth_url = os.environ.get("AUTH_INTERNAL_URL", "http://auth:8000")
        return cls._auth_url


def _auth_headers(request: Request) -> dict[str, str]:
    """Extract the Authorization header from the incoming request."""
    return {"Authorization": request.headers.get("Authorization", "")}


# ---------------------------------------------------------------------------
# Auth Service proxy routes
# ---------------------------------------------------------------------------


@router.get("/stats")
async def proxy_stats(request: Request):
    """Proxy aggregated tenant stats from Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{auth_url}/api/v1/admin/stats",
            headers=_auth_headers(request),
            params=dict(request.query_params),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.get("/stats/{tenant_id}")
async def proxy_tenant_stats(tenant_id: str, request: Request):
    """Proxy single-tenant stats from Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{auth_url}/api/v1/admin/stats/{tenant_id}",
            headers=_auth_headers(request),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.get("/health")
async def proxy_health(request: Request):
    """Proxy system health status from Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{auth_url}/api/v1/admin/health",
            headers=_auth_headers(request),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.get("/tenants")
async def proxy_tenants_list(request: Request):
    """Proxy tenant list from Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{auth_url}/api/v1/tenants",
            headers=_auth_headers(request),
            params=dict(request.query_params),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.get("/tenants/{tenant_id}")
async def proxy_tenant_detail(tenant_id: str, request: Request):
    """Proxy single tenant detail from Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{auth_url}/api/v1/tenants/{tenant_id}",
            headers=_auth_headers(request),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.patch("/tenants/{tenant_id}")
async def proxy_tenant_update(tenant_id: str, request: Request):
    """Proxy tenant update (tier/quota) to Auth Service."""
    auth_url = _Config.auth_url()
    body = await request.body()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{auth_url}/api/v1/tenants/{tenant_id}",
            headers={
                **_auth_headers(request),
                "Content-Type": "application/json",
            },
            content=body,
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.post("/tenants/{tenant_id}/suspend")
async def proxy_tenant_suspend(tenant_id: str, request: Request):
    """Proxy tenant suspend to Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{auth_url}/api/v1/tenants/{tenant_id}/suspend",
            headers=_auth_headers(request),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


@router.post("/tenants/{tenant_id}/reactivate")
async def proxy_tenant_reactivate(tenant_id: str, request: Request):
    """Proxy tenant reactivate to Auth Service."""
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{auth_url}/api/v1/tenants/{tenant_id}/reactivate",
            headers=_auth_headers(request),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Langflow-native route: tenant flows (queries Langflow DB, not Auth proxy)
# ---------------------------------------------------------------------------


@router.get("/tenants/{tenant_id}/flows")
async def get_tenant_flows(tenant_id: str, request: Request):
    """Get flows belonging to a tenant from Langflow's own DB.

    Validates Platform Admin JWT by proxying to Auth Service's /users/me
    endpoint. This ensures the Auth Service remains the single source of
    truth for user identity and role checks.
    """
    # Validate admin JWT by calling Auth Service
    auth_url = _Config.auth_url()
    async with httpx.AsyncClient(timeout=5) as client:
        auth_resp = await client.get(
            f"{auth_url}/api/v1/auth/me",
            headers=_auth_headers(request),
        )
    if auth_resp.status_code != HTTPStatus.OK:
        return Response(
            content=auth_resp.content,
            status_code=auth_resp.status_code,
            media_type="application/json",
        )
    user = auth_resp.json()
    if not user.get("is_platform_admin"):
        return Response(
            content='{"detail":"Platform administrator access required"}',
            status_code=HTTPStatus.FORBIDDEN,
            media_type="application/json",
        )

    # Query Langflow DB for tenant flows
    db_service = get_db_service()
    async with db_service.with_session() as session:
        result = await session.execute(select(Flow).where(Flow.tenant_id == tenant_id))
        flows = result.scalars().all()

    return [
        {
            "id": str(flow.id),
            "name": flow.name,
            "is_component": flow.is_component,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None,
        }
        for flow in flows
    ]

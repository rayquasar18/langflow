"""Tenant context middleware for multi-tenant Langflow.

Provides:
- TenantContextMiddleware: Initializes request.state tenant attributes before handlers run
- tenant_scoped_query(): Adds WHERE tenant_id = ? to any query on a tenant-scoped model
- tenant_scoped_query_with_system(): Same but includes system content (tenant_id IS NULL)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import or_
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from starlette.requests import Request

EXEMPT_PREFIXES = (
    "/health",
    "/api/v1/version",
    "/.well-known/",
    "/api/v1/login/session",
)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Initializes request.state tenant attributes to None before the route handler runs.

    The actual values are populated by get_current_user() in utils.py after JWT
    validation. This middleware ensures the attributes exist so accessing them
    before auth (e.g., in public endpoints or error handlers) does not raise
    AttributeError.
    """

    async def dispatch(self, request, call_next):
        # Skip exempt paths (health checks, public endpoints)
        if any(request.url.path.startswith(p) for p in EXEMPT_PREFIXES):
            return await call_next(request)

        # Initialize state attributes so they exist even if auth is skipped
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.role = None
        request.state.tier = None
        request.state.is_platform_admin = False

        return await call_next(request)


def tenant_scoped_query(stmt, model, request: Request):
    """Add WHERE tenant_id = ? to any query on a tenant-scoped model.

    Raises:
        HTTPException(401): If no tenant context is available on request.state.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="No tenant context")
    return stmt.where(model.tenant_id == tenant_id)


def tenant_scoped_query_with_system(stmt, model, request: Request):
    """Add WHERE (tenant_id = ? OR tenant_id IS NULL) for queries that include system content.

    System/starter content has NULL tenant_id and is visible to all tenants.

    Raises:
        HTTPException(401): If no tenant context is available on request.state.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="No tenant context")
    return stmt.where(or_(model.tenant_id == tenant_id, model.tenant_id.is_(None)))

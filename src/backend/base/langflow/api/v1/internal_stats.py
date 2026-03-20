"""Internal stats endpoint for service-to-service calls from Auth Service.

Exposes tenant-level flow count and request count for admin dashboard
aggregation. Protected by INTERNAL_SERVICE_KEY header check.

Routes:
    GET /internal/stats/{tenant_id}  -- Flow count and request count for tenant
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select

from langflow.services.database.models.flow.model import Flow
from langflow.services.deps import get_db_service

router = APIRouter(prefix="/internal", tags=["internal"])


class _Config:
    """Lazy-initialized config container to avoid module-level env reads."""

    _service_key: str | None = None

    @classmethod
    def service_key(cls) -> str:
        if cls._service_key is None:
            cls._service_key = os.environ.get("INTERNAL_SERVICE_KEY", "")
        return cls._service_key


def _verify_service_key(request: Request) -> None:
    """Verify the X-Service-Key header matches the configured key."""
    expected = _Config.service_key()
    provided = request.headers.get("X-Service-Key", "")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid service key")


@router.get("/stats/{tenant_id}")
async def get_tenant_stats(tenant_id: str, request: Request):
    """Get flow count and request count for a tenant.

    Protected by X-Service-Key header. Called by Auth Service for admin
    dashboard stats aggregation.
    """
    _verify_service_key(request)

    db_service = get_db_service()
    async with db_service.with_session() as session:
        # Count flows belonging to this tenant
        result = await session.execute(select(func.count()).select_from(Flow).where(Flow.tenant_id == tenant_id))
        flow_count = result.scalar() or 0

    # Request count: not currently tracked in Langflow DB.
    # Return 0 until analytics table exists (can be enhanced later).
    request_count = 0

    return {"flow_count": flow_count, "request_count": request_count}

"""Quota enforcement, feature gating, and component filtering for Langflow.

Provides FastAPI dependencies and utility functions for tier-based enforcement:
- require_quota(quota_type): Factory returning a dependency that checks resource limits
- require_feature(feature): Factory returning a dependency that checks feature flags
- check_rate_limit: Dependency that enforces per-minute request limits
- filter_components_by_tier(): Pure function to remove gated components from /all response

All enforcement reads tier from request.state (populated by TenantContextMiddleware
and get_current_user). Platform Admin bypasses all checks.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from lfx.services.deps import injectable_session_scope
from sqlalchemy import func
from sqlmodel import select

from langflow.services.database.models.flow.model import Flow

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

# ---------------------------------------------------------------------------
# Tier definitions (local copy)
# ---------------------------------------------------------------------------
# Matches auth/app/services/tier.py schema — keep in sync
#
# Both services use identical nested structure:
#   tier -> display_name, quotas (max_flows, max_kb_docs, max_requests_per_minute), features (set)
# Langflow cannot import from auth (separate Python package), so this is
# a maintained copy. When adding tiers or changing quotas, update BOTH files.

TIER_DEFINITIONS: dict[str, dict] = {
    "free": {
        "display_name": "Free",
        "quotas": {"max_flows": 5, "max_kb_docs": 50, "max_requests_per_minute": 20},
        "features": {
            "basic_rag",
            "basic_flows",
        },
    },
    "pro": {
        "display_name": "Pro",
        "quotas": {"max_flows": 50, "max_kb_docs": 500, "max_requests_per_minute": 100},
        "features": {
            "basic_rag",
            "basic_flows",
            "advanced_rag",
            "custom_components",
        },
    },
    "enterprise": {
        "display_name": "Enterprise",
        "quotas": {"max_flows": -1, "max_kb_docs": -1, "max_requests_per_minute": -1},
        "features": {
            "basic_rag",
            "basic_flows",
            "advanced_rag",
            "custom_components",
            "graphrag",
        },
    },
}


def get_tier_config(tier_name: str) -> dict:
    """Return the tier configuration for *tier_name*.

    Falls back to the ``free`` tier for any unrecognised name.
    """
    return TIER_DEFINITIONS.get(tier_name, TIER_DEFINITIONS["free"])


# ---------------------------------------------------------------------------
# Tier-gated component mapping
# ---------------------------------------------------------------------------
# Maps feature flags to component class names that require that feature.
# Components whose feature flag is NOT in the tenant's tier are hidden from
# the /all response.

TIER_GATED_COMPONENTS: dict[str, set[str]] = {
    "advanced_rag": {"RagflowIngestDocument"},
    "custom_components": {"CustomComponent"},
    "graphrag": set(),  # Future: GraphRAG nodes
}


# ---------------------------------------------------------------------------
# require_quota factory
# ---------------------------------------------------------------------------


def require_quota(quota_type: str):
    """Factory returning a FastAPI dependency that checks a resource quota.

    Usage::

        @router.post("/", dependencies=[Depends(require_quota("max_flows"))])
        async def create_flow(...): ...
    """

    async def _check_quota(
        request: Request,
        session: AsyncSession = Depends(injectable_session_scope),
    ) -> None:
        # Platform Admin bypass
        if getattr(request.state, "is_platform_admin", False):
            return

        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="No tenant context")

        tier = getattr(request.state, "tier", None) or "free"
        tier_config = get_tier_config(tier)
        limit = tier_config["quotas"].get(quota_type)

        if limit is None:
            # Unknown quota type — allow (safe default; log in production)
            return

        if limit == -1:
            # Unlimited
            return

        # Count current resources
        if quota_type == "max_flows":
            result = await session.exec(select(func.count(Flow.id)).where(Flow.tenant_id == tenant_id))
            current_count = result.one()
        else:
            # For other quota types, allow by default (not yet implemented)
            return

        if current_count >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "quota_type": quota_type,
                    "limit": limit,
                    "current": current_count,
                    "tier": tier,
                    "message": (
                        f"Quota exceeded: {quota_type} limit is {limit} for "
                        f"{tier} tier (current: {current_count}). "
                        f"Upgrade your plan to increase this limit."
                    ),
                },
            )

    return _check_quota


# ---------------------------------------------------------------------------
# require_feature factory
# ---------------------------------------------------------------------------


def require_feature(feature: str):
    """Factory returning a FastAPI dependency that checks a feature flag.

    Usage::

        @router.post("/code", dependencies=[Depends(require_feature("custom_components"))])
        async def post_validate_code(...): ...
    """

    async def _check_feature(request: Request) -> None:
        # Platform Admin bypass
        if getattr(request.state, "is_platform_admin", False):
            return

        tier = getattr(request.state, "tier", None) or "free"
        tier_config = get_tier_config(tier)

        if feature not in tier_config["features"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_not_available",
                    "feature": feature,
                    "tier": tier,
                    "message": (
                        f"Feature '{feature}' is not available on the {tier} tier. "
                        f"Upgrade your plan to access this feature."
                    ),
                },
            )

    return _check_feature


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-process)
# ---------------------------------------------------------------------------
# For v1: simple in-memory counter with minute-bucket keys.
# Sufficient for single-process Docker deployment. Swap to Redis for scale.

_rate_counters: dict[str, int] = {}
_rate_state: dict[str, float] = {"last_cleanup": 0.0}
_CLEANUP_INTERVAL_SECONDS = 120.0


def _current_minute_bucket() -> str:
    """Return a string key for the current UTC minute."""
    return str(int(time.time()) // 60)


def _cleanup_stale_counters() -> None:
    """Remove counter entries older than the current minute bucket."""
    now = time.time()
    if now - _rate_state["last_cleanup"] < _CLEANUP_INTERVAL_SECONDS:
        return
    _rate_state["last_cleanup"] = now
    current_bucket = _current_minute_bucket()
    stale_keys = [k for k in _rate_counters if not k.endswith(f":{current_bucket}")]
    for k in stale_keys:
        del _rate_counters[k]


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency that enforces per-minute request rate limits.

    Reads tier and tenant_id from request.state.
    """
    # Platform Admin bypass
    if getattr(request.state, "is_platform_admin", False):
        return

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        return  # No tenant context — skip rate limiting (handled by quota check)

    tier = getattr(request.state, "tier", None) or "free"
    tier_config = get_tier_config(tier)
    limit = tier_config["quotas"].get("max_requests_per_minute", -1)

    if limit == -1:
        return  # Unlimited

    bucket = _current_minute_bucket()
    key = f"{tenant_id}:{bucket}"

    # Periodic cleanup
    _cleanup_stale_counters()

    current = _rate_counters.get(key, 0)
    if current >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "limit": limit,
                "tier": tier,
                "message": (
                    f"Rate limit exceeded: {limit} requests per minute for {tier} tier. Please wait and try again."
                ),
            },
        )

    _rate_counters[key] = current + 1


# ---------------------------------------------------------------------------
# Component filtering by tier
# ---------------------------------------------------------------------------


def filter_components_by_tier(all_types: dict, tier: str) -> dict:
    """Filter component types dict to remove components gated by features the tier lacks.

    Args:
        all_types: The full component types dict from get_and_cache_all_types_dict.
                   Structure: ``{"category_name": {"ComponentName": {...}, ...}, ...}``
        tier: The tenant's tier name (e.g. "free", "pro", "enterprise").

    Returns:
        A new dict with gated components removed. Empty categories are excluded.
    """
    tier_config = get_tier_config(tier)
    tier_features = tier_config["features"]

    # Build set of blocked component names
    blocked: set[str] = set()
    for feature, component_names in TIER_GATED_COMPONENTS.items():
        if feature not in tier_features:
            blocked |= component_names

    if not blocked:
        return all_types

    filtered: dict = {}
    for category, components in all_types.items():
        if not isinstance(components, dict):
            # Non-dict entries (metadata, etc.) pass through
            filtered[category] = components
            continue

        filtered_components = {name: spec for name, spec in components.items() if name not in blocked}
        if filtered_components:
            filtered[category] = filtered_components

    return filtered

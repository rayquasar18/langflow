"""Unit tests for tenant_id injection into graph context.

Verifies that build_graph_from_data passes context through to Graph.from_payload,
and that build_graph_from_db_no_cache injects flow.tenant_id (dash-stripped)
into context for downstream component access via self.graph.context.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_flow():
    """Create a mock Flow object with tenant_id."""
    flow = MagicMock()
    flow.id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    flow.data = {"nodes": [], "edges": []}
    flow.name = "test-flow"
    flow.user_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    flow.tenant_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")  # pragma: allowlist secret
    return flow


@pytest.fixture
def mock_session(mock_flow):
    """Create a mock async session that returns mock_flow."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=mock_flow)
    return session


class TestBuildGraphFromDataContext:
    """Test that build_graph_from_data passes context to Graph.from_payload."""

    @pytest.mark.asyncio
    async def test_context_kwarg_passed_through(self):
        """When context is provided, it should reach Graph.from_payload."""
        context = {"tenant_id": "abc123", "extra": "value"}

        with (
            patch(
                "langflow.api.utils.core.Graph.from_payload",
                return_value=MagicMock(
                    has_session_id_vertices=[],
                    session_id=None,
                    initialize_run=AsyncMock(),
                ),
            ) as mock_from_payload,
            patch(
                "langflow.api.utils.core._get_flow_name",
                new_callable=AsyncMock,
                return_value="test-flow",
            ),
        ):
            from langflow.api.utils.core import build_graph_from_data

            flow_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
            await build_graph_from_data(
                flow_id,
                {"nodes": [], "edges": []},
                flow_name="test-flow",
                user_id="uid",
                context=context,
            )

            mock_from_payload.assert_called_once()
            call_kwargs = mock_from_payload.call_args
            # context should be passed as keyword arg
            assert call_kwargs.kwargs.get("context") == context

    @pytest.mark.asyncio
    async def test_no_context_passes_none(self):
        """When no context is provided, None should be passed."""
        with (
            patch(
                "langflow.api.utils.core.Graph.from_payload",
                return_value=MagicMock(
                    has_session_id_vertices=[],
                    session_id=None,
                    initialize_run=AsyncMock(),
                ),
            ) as mock_from_payload,
            patch(
                "langflow.api.utils.core._get_flow_name",
                new_callable=AsyncMock,
                return_value="test-flow",
            ),
        ):
            from langflow.api.utils.core import build_graph_from_data

            flow_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
            await build_graph_from_data(
                flow_id,
                {"nodes": [], "edges": []},
                flow_name="test-flow",
                user_id="uid",
            )

            mock_from_payload.assert_called_once()
            call_kwargs = mock_from_payload.call_args
            assert call_kwargs.kwargs.get("context") is None


class TestBuildGraphFromDbNoCache:
    """Test tenant_id injection in build_graph_from_db_no_cache."""

    @pytest.mark.asyncio
    async def test_tenant_id_injected_dash_stripped(self, mock_session, mock_flow):
        """flow.tenant_id with dashes should be stripped to 32-char hex."""
        with patch(
            "langflow.api.utils.core.build_graph_from_data",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = MagicMock()
            from langflow.api.utils.core import build_graph_from_db_no_cache

            await build_graph_from_db_no_cache(mock_flow.id, mock_session)

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            ctx = call_kwargs.get("context", {})
            assert "tenant_id" in ctx
            assert ctx["tenant_id"] == "550e8400e29b41d4a716446655440000"  # pragma: allowlist secret
            assert len(ctx["tenant_id"]) == 32

    @pytest.mark.asyncio
    async def test_tenant_id_none_not_in_context(self, mock_session, mock_flow):
        """When flow.tenant_id is None, context should not contain tenant_id."""
        mock_flow.tenant_id = None

        with patch(
            "langflow.api.utils.core.build_graph_from_data",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = MagicMock()
            from langflow.api.utils.core import build_graph_from_db_no_cache

            await build_graph_from_db_no_cache(mock_flow.id, mock_session)

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            ctx = call_kwargs.get("context", {})
            assert "tenant_id" not in ctx

    @pytest.mark.asyncio
    async def test_existing_context_preserved(self, mock_session, mock_flow):
        """Existing context values from kwargs should be preserved alongside tenant_id."""
        with patch(
            "langflow.api.utils.core.build_graph_from_data",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = MagicMock()
            from langflow.api.utils.core import build_graph_from_db_no_cache

            await build_graph_from_db_no_cache(
                mock_flow.id,
                mock_session,
                context={"existing_key": "existing_value"},
            )

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            ctx = call_kwargs.get("context", {})
            # Both existing and injected values present
            assert ctx["existing_key"] == "existing_value"
            assert ctx["tenant_id"] == "550e8400e29b41d4a716446655440000"  # pragma: allowlist secret

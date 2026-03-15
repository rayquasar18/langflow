"""Unit tests for RagflowManageKnowledgeBase component.

Tests component structure, create/list/delete actions, input validation,
and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Test UUIDs (not secrets)
_TEST_TENANT_UUID = "550e8400-e29b-41d4-a716-446655440000"  # pragma: allowlist secret
_TEST_USER_UUID = "660e8400-e29b-41d4-a716-446655440000"  # pragma: allowlist secret
_TEST_TENANT_HEX = "550e8400e29b41d4a716446655440000"  # pragma: allowlist secret
_TEST_USER_HEX = "660e8400e29b41d4a716446655440000"  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_module_globals(monkeypatch):
    """Reset module-level cached config between tests."""
    import lfx.components.ragflow._client as mod

    monkeypatch.setattr(mod, "_RAGFLOW_URL", None)
    monkeypatch.setattr(mod, "_RAGFLOW_SERVICE_KEY", None)
    monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
    monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "test-key")


def _make_component(action="list", kb_name="", kb_ids="", context=None):
    """Create a RagflowManageKnowledgeBase with a mock vertex providing graph context."""
    from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

    comp = RagflowManageKnowledgeBase(_user_id=_TEST_USER_UUID)
    mock_graph = MagicMock()
    mock_graph.context = context if context is not None else {"tenant_id": _TEST_TENANT_HEX}
    mock_graph.user_id = _TEST_USER_UUID
    mock_vertex = MagicMock()
    mock_vertex.graph = mock_graph
    comp._vertex = mock_vertex
    # Set input values
    comp.action = action
    comp.kb_name = kb_name
    comp.kb_ids = kb_ids
    comp.page = 1
    comp.page_size = 30
    return comp


@pytest.fixture
def list_component():
    """Component configured for list action."""
    return _make_component(action="list")


@pytest.fixture
def create_component():
    """Component configured for create action."""
    return _make_component(action="create", kb_name="My Knowledge Base")


@pytest.fixture
def delete_component():
    """Component configured for delete action."""
    return _make_component(action="delete", kb_ids="kb-001,kb-002")


# ---------------------------------------------------------------------------
# Class structure tests
# ---------------------------------------------------------------------------


class TestComponentStructure:
    def test_inherits_from_component(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase
        from lfx.custom.custom_component.component import Component

        assert issubclass(RagflowManageKnowledgeBase, Component)

    def test_display_name(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        assert RagflowManageKnowledgeBase.display_name == "RAGFlow Knowledge Base"

    def test_name_is_stable(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        assert RagflowManageKnowledgeBase.name == "RagflowManageKnowledgeBase"

    def test_has_action_input(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        input_names = [i.name for i in RagflowManageKnowledgeBase.inputs]
        assert "action" in input_names

    def test_action_has_correct_options(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        action_input = next(i for i in RagflowManageKnowledgeBase.inputs if i.name == "action")
        assert set(action_input.options) == {"create", "list", "delete"}

    def test_has_kb_name_input(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        input_names = [i.name for i in RagflowManageKnowledgeBase.inputs]
        assert "kb_name" in input_names

    def test_has_kb_ids_input(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        input_names = [i.name for i in RagflowManageKnowledgeBase.inputs]
        assert "kb_ids" in input_names

    def test_has_json_output(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        output_display_names = [o.display_name for o in RagflowManageKnowledgeBase.outputs]
        assert "JSON" in output_display_names

    def test_has_table_output(self):
        from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase

        output_display_names = [o.display_name for o in RagflowManageKnowledgeBase.outputs]
        assert "Table" in output_display_names


# ---------------------------------------------------------------------------
# Create action tests
# ---------------------------------------------------------------------------


class TestCreateAction:
    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_create_calls_create_dataset(self, mock_get_client, create_component):
        """Test create action calls client.create_dataset with kb_name."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_dataset.return_value = {
            "code": 0,
            "data": {"id": "kb-new-001", "name": "My Knowledge Base"},
        }

        result = create_component.manage_kb()

        mock_client.create_dataset.assert_called_once_with(name="My Knowledge Base")
        assert result.data["data"]["id"] == "kb-new-001"

    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_create_with_empty_name_returns_error(self, mock_get_client):
        """Test that creating with empty name returns error Data."""
        comp = _make_component(action="create", kb_name="")

        result = comp.manage_kb()

        assert "error" in result.data
        mock_get_client.assert_not_called()


# ---------------------------------------------------------------------------
# List action tests
# ---------------------------------------------------------------------------


class TestListAction:
    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_list_calls_list_datasets(self, mock_get_client, list_component):
        """Test list action calls client.list_datasets."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_datasets.return_value = {
            "code": 0,
            "data": [
                {"id": "kb-001", "name": "KB One"},
                {"id": "kb-002", "name": "KB Two"},
            ],
        }

        result = list_component.manage_kb()

        mock_client.list_datasets.assert_called_once_with(page=1, page_size=30)
        assert len(result.data["data"]) == 2

    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_list_passes_pagination_params(self, mock_get_client, list_component):
        """Test that page and page_size params are passed to client."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_datasets.return_value = {"code": 0, "data": []}
        list_component.page = 3
        list_component.page_size = 10

        list_component.manage_kb()

        mock_client.list_datasets.assert_called_once_with(page=3, page_size=10)


# ---------------------------------------------------------------------------
# Delete action tests
# ---------------------------------------------------------------------------


class TestDeleteAction:
    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_delete_calls_delete_datasets(self, mock_get_client, delete_component):
        """Test delete action calls client.delete_datasets with parsed IDs."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete_datasets.return_value = {"code": 0}

        result = delete_component.manage_kb()

        mock_client.delete_datasets.assert_called_once_with(["kb-001", "kb-002"])
        assert "error" not in result.data

    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_delete_with_empty_ids_returns_error(self, mock_get_client):
        """Test that deleting with empty IDs returns error Data."""
        comp = _make_component(action="delete", kb_ids="")

        result = comp.manage_kb()

        assert "error" in result.data
        mock_get_client.assert_not_called()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_ragflow_error_code(self, mock_get_client, list_component):
        """Test that non-zero RAGFlow response code is handled."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_datasets.return_value = {
            "code": 103,
            "message": "Internal error",
        }

        result = list_component.manage_kb()

        assert "error" in result.data

    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_http_error_returns_error_data(self, mock_get_client, list_component):
        """Test that HTTP errors are caught and return error Data."""
        import httpx

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_datasets.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        result = list_component.manage_kb()

        assert "error" in result.data

    @patch("lfx.components.ragflow.manage_kb.get_ragflow_client")
    def test_table_output_returns_dataframe(self, mock_get_client, list_component):
        """Test manage_kb_table wraps result in DataFrame."""
        from lfx.schema.dataframe import DataFrame

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_datasets.return_value = {
            "code": 0,
            "data": [{"id": "kb-001", "name": "Test"}],
        }

        result = list_component.manage_kb_table()

        assert isinstance(result, DataFrame)

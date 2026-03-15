"""Unit tests for RagflowIngestDocument component.

Tests component structure, file ingestion flow, error handling,
and tenant_id resolution from graph context.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Test UUIDs (not secrets)
_TEST_TENANT_UUID = "550e8400-e29b-41d4-a716-446655440000"  # pragma: allowlist secret
_TEST_USER_UUID = "660e8400-e29b-41d4-a716-446655440000"  # pragma: allowlist secret
_TEST_TENANT_HEX = "550e8400e29b41d4a716446655440000"  # pragma: allowlist secret
_TEST_USER_HEX = "660e8400e29b41d4a716446655440000"  # pragma: allowlist secret
_TEST_DATASET_ID = "ds-abc123"


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


def _make_component(context: dict | None = None):
    """Create a RagflowIngestDocument with a mock vertex providing graph context."""
    from lfx.components.ragflow.ingest import RagflowIngestDocument

    comp = RagflowIngestDocument(_user_id=_TEST_USER_UUID)
    # Wire up a mock vertex so comp.graph returns a mock with our context
    mock_graph = MagicMock()
    mock_graph.context = context if context is not None else {"tenant_id": _TEST_TENANT_HEX}
    mock_graph.user_id = _TEST_USER_UUID
    mock_vertex = MagicMock()
    mock_vertex.graph = mock_graph
    comp._vertex = mock_vertex
    # Set input attribute values directly
    comp.dataset_id = _TEST_DATASET_ID
    comp.file = "/tmp/test-doc.pdf"
    return comp


@pytest.fixture
def component():
    """Create a RagflowIngestDocument component with tenant_id in context."""
    return _make_component(context={"tenant_id": _TEST_TENANT_HEX})


@pytest.fixture
def component_no_tenant():
    """Create component with no tenant_id in graph context (fallback scenario)."""
    return _make_component(context={})


# ---------------------------------------------------------------------------
# Class structure tests
# ---------------------------------------------------------------------------


class TestComponentStructure:
    def test_inherits_from_component(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument
        from lfx.custom.custom_component.component import Component

        assert issubclass(RagflowIngestDocument, Component)

    def test_display_name(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        assert RagflowIngestDocument.display_name == "RAGFlow Document Ingestion"

    def test_name_is_stable(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        assert RagflowIngestDocument.name == "RagflowIngestDocument"

    def test_has_dataset_id_input(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        input_names = [i.name for i in RagflowIngestDocument.inputs]
        assert "dataset_id" in input_names

    def test_has_file_input(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        input_names = [i.name for i in RagflowIngestDocument.inputs]
        assert "file" in input_names

    def test_dataset_id_is_required(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        ds_input = next(i for i in RagflowIngestDocument.inputs if i.name == "dataset_id")
        assert ds_input.required is True

    def test_file_is_required(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        file_input = next(i for i in RagflowIngestDocument.inputs if i.name == "file")
        assert file_input.required is True

    def test_output_method_is_ingest_document(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        output_methods = [o.method for o in RagflowIngestDocument.outputs]
        assert "ingest_document" in output_methods

    def test_output_display_name_is_json(self):
        from lfx.components.ragflow.ingest import RagflowIngestDocument

        output_names = [o.display_name for o in RagflowIngestDocument.outputs]
        assert "JSON" in output_names


# ---------------------------------------------------------------------------
# Ingestion flow tests
# ---------------------------------------------------------------------------


class TestIngestionFlow:
    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_successful_upload_and_parse(self, mock_get_client, mock_run, component):
        """Test the full upload -> parse flow returns correct Data."""
        mock_run.return_value = b"fake-pdf-content"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {
            "code": 0,
            "data": [{"id": "doc-001"}],
        }
        mock_client.parse_documents.return_value = {"code": 0, "data": True}

        result = component.ingest_document()

        assert result.data["document_ids"] == ["doc-001"]
        assert result.data["dataset_id"] == _TEST_DATASET_ID
        assert result.data["status"] == "parsing_started"
        assert result.data["filename"] == "test-doc.pdf"

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_calls_upload_with_correct_args(self, mock_get_client, mock_run, component):
        """Test that upload_document is called with correct file bytes and name."""
        mock_run.return_value = b"the-bytes"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {
            "code": 0,
            "data": [{"id": "doc-x"}],
        }
        mock_client.parse_documents.return_value = {"code": 0}

        component.ingest_document()

        mock_client.upload_document.assert_called_once_with(_TEST_DATASET_ID, b"the-bytes", "test-doc.pdf")

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_calls_parse_with_document_ids(self, mock_get_client, mock_run, component):
        """Test that parse_documents is called with extracted doc IDs."""
        mock_run.return_value = b"content"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {
            "code": 0,
            "data": [{"id": "d1"}, {"id": "d2"}],
        }
        mock_client.parse_documents.return_value = {"code": 0}

        result = component.ingest_document()

        mock_client.parse_documents.assert_called_once_with(_TEST_DATASET_ID, ["d1", "d2"])
        assert result.data["document_ids"] == ["d1", "d2"]

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_uses_resolve_path_for_file(self, mock_get_client, mock_run, component):
        """Test that resolve_path is used on the file input."""
        mock_run.return_value = b"data"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {"code": 0, "data": [{"id": "d1"}]}
        mock_client.parse_documents.return_value = {"code": 0}

        with patch.object(component, "resolve_path", return_value="/resolved/test-doc.pdf") as mock_resolve:
            component.ingest_document()
            mock_resolve.assert_called_once_with("/tmp/test-doc.pdf")


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_ragflow_error_code_returns_error_data(self, mock_get_client, mock_run, component):
        """Test that non-zero RAGFlow response code returns error Data."""
        mock_run.return_value = b"content"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {
            "code": 102,
            "message": "Dataset not found",
        }

        result = component.ingest_document()

        assert "error" in result.data
        assert "Dataset not found" in result.data["error"]

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_http_error_returns_error_data(self, mock_get_client, mock_run, component):
        """Test that HTTP errors are caught and return error Data."""
        import httpx

        mock_run.return_value = b"content"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        result = component.ingest_document()

        assert "error" in result.data

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_timeout_returns_error_data(self, mock_get_client, mock_run, component):
        """Test that timeout exceptions are caught and return error Data."""
        import httpx

        mock_run.return_value = b"content"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.side_effect = httpx.TimeoutException("timed out")

        result = component.ingest_document()

        assert "error" in result.data


# ---------------------------------------------------------------------------
# Tenant resolution tests
# ---------------------------------------------------------------------------


class TestTenantResolution:
    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_tenant_id_from_context(self, mock_get_client, mock_run, component):
        """Test that tenant_id is resolved from graph context."""
        mock_run.return_value = b"data"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {"code": 0, "data": [{"id": "d1"}]}
        mock_client.parse_documents.return_value = {"code": 0}

        component.ingest_document()

        mock_get_client.assert_called_once_with(_TEST_TENANT_HEX, _TEST_USER_HEX)

    @patch("lfx.components.ragflow.ingest.run_until_complete")
    @patch("lfx.components.ragflow.ingest.get_ragflow_client")
    def test_tenant_id_fallback_to_user_id(self, mock_get_client, mock_run, component_no_tenant):
        """Test fallback: when no tenant_id in context, use user_id with dashes stripped."""
        mock_run.return_value = b"data"
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.upload_document.return_value = {"code": 0, "data": [{"id": "d1"}]}
        mock_client.parse_documents.return_value = {"code": 0}

        component_no_tenant.ingest_document()

        # Both tenant_id and user_id should be the user_id with dashes stripped
        mock_get_client.assert_called_once_with(_TEST_USER_HEX, _TEST_USER_HEX)

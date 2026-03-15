"""Unit tests for RagflowRetrieve component.

Tests component structure, retrieval flow with hybrid search params,
error handling, and output formats (Table + JSON).
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


def _make_component(context=None):
    """Create a RagflowRetrieve with a mock vertex providing graph context."""
    from lfx.components.ragflow.retrieve import RagflowRetrieve

    comp = RagflowRetrieve(_user_id=_TEST_USER_UUID)
    mock_graph = MagicMock()
    mock_graph.context = context if context is not None else {"tenant_id": _TEST_TENANT_HEX}
    mock_graph.user_id = _TEST_USER_UUID
    mock_vertex = MagicMock()
    mock_vertex.graph = mock_graph
    comp._vertex = mock_vertex
    # Set input values
    comp.query = "What is deep learning?"
    comp.dataset_ids = "ds-001,ds-002"
    comp.top_k = 5
    comp.similarity_threshold = 0.2
    comp.vector_similarity_weight = 0.3
    comp.highlight = True
    return comp


@pytest.fixture
def component():
    """Create a RagflowRetrieve component with tenant context."""
    return _make_component()


def _sample_chunks():
    """Return sample RAGFlow retrieval response chunks."""
    return {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "id": "chunk-1",
                    "content": "Deep learning is a subset of machine learning.",
                    "similarity": 0.92,
                    "doc_name": "ml-intro.pdf",
                    "highlight": "Deep <em>learning</em> is a subset...",
                },
                {
                    "id": "chunk-2",
                    "content": "Neural networks form the basis of deep learning.",
                    "similarity": 0.85,
                    "doc_name": "nn-guide.pdf",
                    "highlight": "Neural networks form the basis of <em>deep learning</em>.",
                },
            ]
        },
    }


# ---------------------------------------------------------------------------
# Class structure tests
# ---------------------------------------------------------------------------


class TestComponentStructure:
    def test_inherits_from_component(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve
        from lfx.custom.custom_component.component import Component

        assert issubclass(RagflowRetrieve, Component)

    def test_display_name(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        assert RagflowRetrieve.display_name == "RAGFlow Retrieval"

    def test_name_is_stable(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        assert RagflowRetrieve.name == "RagflowRetrieve"

    def test_has_query_input(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        input_names = [i.name for i in RagflowRetrieve.inputs]
        assert "query" in input_names

    def test_query_has_tool_mode(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        query_input = next(i for i in RagflowRetrieve.inputs if i.name == "query")
        assert query_input.tool_mode is True

    def test_has_dataset_ids_input(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        input_names = [i.name for i in RagflowRetrieve.inputs]
        assert "dataset_ids" in input_names

    def test_has_top_k_input(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        input_names = [i.name for i in RagflowRetrieve.inputs]
        assert "top_k" in input_names

    def test_has_similarity_threshold_input(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        input_names = [i.name for i in RagflowRetrieve.inputs]
        assert "similarity_threshold" in input_names

    def test_has_vector_similarity_weight_input(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        input_names = [i.name for i in RagflowRetrieve.inputs]
        assert "vector_similarity_weight" in input_names

    def test_has_table_output(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        output_display_names = [o.display_name for o in RagflowRetrieve.outputs]
        assert "Table" in output_display_names

    def test_has_json_output(self):
        from lfx.components.ragflow.retrieve import RagflowRetrieve

        output_display_names = [o.display_name for o in RagflowRetrieve.outputs]
        assert "JSON" in output_display_names


# ---------------------------------------------------------------------------
# Retrieval flow tests
# ---------------------------------------------------------------------------


class TestRetrievalFlow:
    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_retrieve_json_returns_data_list(self, mock_get_client, component):
        """Test retrieve_json returns list of Data objects with chunk content."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = _sample_chunks()

        result = component.retrieve_json()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].data["content"] == "Deep learning is a subset of machine learning."
        assert result[0].data["similarity"] == 0.92
        assert result[1].data["doc_name"] == "nn-guide.pdf"

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_retrieve_table_returns_dataframe(self, mock_get_client, component):
        """Test retrieve_table returns a DataFrame."""
        from lfx.schema.dataframe import DataFrame

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = _sample_chunks()

        result = component.retrieve_table()

        assert isinstance(result, DataFrame)

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_dataset_ids_comma_parsing(self, mock_get_client, component):
        """Test that dataset_ids are split on commas correctly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = {"code": 0, "data": {"chunks": []}}

        component.retrieve_json()

        call_kwargs = mock_client.retrieval.call_args.kwargs
        assert call_kwargs["dataset_ids"] == ["ds-001", "ds-002"]

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_all_params_passed_to_client(self, mock_get_client, component):
        """Test that all search params are passed correctly to the client."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = {"code": 0, "data": {"chunks": []}}

        component.top_k = 10
        component.similarity_threshold = 0.5
        component.vector_similarity_weight = 0.7

        component.retrieve_json()

        call_kwargs = mock_client.retrieval.call_args.kwargs
        assert call_kwargs["question"] == "What is deep learning?"
        assert call_kwargs["top_k"] == 10
        assert call_kwargs["similarity_threshold"] == 0.5
        assert call_kwargs["vector_similarity_weight"] == 0.7

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_empty_results_returns_empty_list(self, mock_get_client, component):
        """Test that zero chunks returns empty list (not error)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = {"code": 0, "data": {"chunks": []}}

        result = component.retrieve_json()

        assert result == []

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_empty_results_returns_empty_dataframe(self, mock_get_client, component):
        """Test that zero chunks returns empty DataFrame (not error)."""
        from lfx.schema.dataframe import DataFrame

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = {"code": 0, "data": {"chunks": []}}

        result = component.retrieve_table()

        assert isinstance(result, DataFrame)

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_chunk_data_has_expected_fields(self, mock_get_client, component):
        """Test each chunk Data has content, similarity, and doc_name."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = _sample_chunks()

        result = component.retrieve_json()

        for item in result:
            assert "content" in item.data
            assert "similarity" in item.data
            assert "doc_name" in item.data


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_ragflow_error_code_returns_empty(self, mock_get_client, component):
        """Test that non-zero RAGFlow response code returns error Data."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.return_value = {
            "code": 102,
            "message": "Dataset not found",
        }

        result = component.retrieve_json()

        # Should return a list with an error Data object
        assert len(result) == 1
        assert "error" in result[0].data

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_http_error_returns_error_data(self, mock_get_client, component):
        """Test that HTTP errors are caught and return error Data."""
        import httpx

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        result = component.retrieve_json()

        assert len(result) == 1
        assert "error" in result[0].data

    @patch("lfx.components.ragflow.retrieve.get_ragflow_client")
    def test_timeout_returns_error_data(self, mock_get_client, component):
        """Test that timeout exceptions are caught and return error Data."""
        import httpx

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.retrieval.side_effect = httpx.TimeoutException("timed out")

        result = component.retrieve_json()

        assert len(result) == 1
        assert "error" in result[0].data

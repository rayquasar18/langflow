"""Unit tests for RagflowClient HTTP helper.

Tests header construction, UUID dash stripping, env var config,
API method calls, and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
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


@pytest.fixture
def mock_client():
    """Provide a mock httpx.Client that records calls."""
    with patch("lfx.components.ragflow._client.httpx.Client") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=instance)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        yield instance


# ---------------------------------------------------------------------------
# Header construction
# ---------------------------------------------------------------------------


class TestHeaders:
    def test_headers_contain_service_key(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "test-secret-key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id=_TEST_TENANT_UUID, user_id=_TEST_USER_UUID)
        headers = client._headers
        assert headers["X-Service-Key"] == "test-secret-key"

    def test_headers_contain_tenant_and_user_ids(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id=_TEST_TENANT_UUID, user_id=_TEST_USER_UUID)
        headers = client._headers
        assert headers["X-Tenant-ID"] == _TEST_TENANT_HEX
        assert headers["X-User-ID"] == _TEST_USER_HEX

    def test_uuid_dash_stripping(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(
            tenant_id="abcdef01-2345-6789-abcd-ef0123456789",
            user_id="11111111-2222-3333-4444-555555555555",
        )
        headers = client._headers
        assert headers["X-Tenant-ID"] == "abcdef0123456789abcdef0123456789"  # pragma: allowlist secret
        assert len(headers["X-Tenant-ID"]) == 32
        assert headers["X-User-ID"] == "11111111222233334444555555555555"
        assert len(headers["X-User-ID"]) == 32

    def test_already_stripped_uuids_unchanged(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id=_TEST_TENANT_HEX, user_id=_TEST_USER_HEX)
        headers = client._headers
        assert headers["X-Tenant-ID"] == _TEST_TENANT_HEX
        assert headers["X-User-ID"] == _TEST_USER_HEX


# ---------------------------------------------------------------------------
# Env var config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_url_fallback(self, monkeypatch):
        monkeypatch.delenv("RAGFLOW_URL", raising=False)
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id="abc", user_id="def")
        assert client.base_url == "http://ragflow:9380"

    def test_custom_url_from_env(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://custom:1234")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "key")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id="abc", user_id="def")
        assert client.base_url == "http://custom:1234"

    def test_default_service_key_empty(self, monkeypatch):
        monkeypatch.delenv("RAGFLOW_SERVICE_KEY", raising=False)
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        from lfx.components.ragflow._client import RagflowClient

        client = RagflowClient(tenant_id="abc", user_id="def")
        assert client._headers["X-Service-Key"] == ""


# ---------------------------------------------------------------------------
# API methods
# ---------------------------------------------------------------------------


class TestAPIMethods:
    def test_list_datasets(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": []}
        mock_client.get.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        result = client.list_datasets(page=1, page_size=30)

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/api/v1/datasets" in call_args[0][0]
        assert result == {"code": 0, "data": []}

    def test_create_dataset(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": {"id": "ds1"}}
        mock_client.post.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        result = client.create_dataset(name="test")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/v1/datasets" in call_args[0][0]
        assert call_args[1]["json"]["name"] == "test"
        assert result == {"code": 0, "data": {"id": "ds1"}}

    def test_delete_datasets(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0}
        mock_client.delete.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        client.delete_datasets(ids=["id1"])

        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args
        assert "/api/v1/datasets" in call_args[0][0]
        assert call_args[1]["json"]["ids"] == ["id1"]

    def test_upload_document(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": {"id": "doc1"}}
        mock_client.post.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        client.upload_document(
            dataset_id="ds1",
            file_bytes=b"hello world",
            filename="test.txt",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/v1/datasets/ds1/documents" in call_args[0][0]
        # multipart: files kwarg present
        assert "files" in call_args[1]

    def test_parse_documents(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0}
        mock_client.post.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        client.parse_documents(
            dataset_id="ds1",
            document_ids=["doc1", "doc2"],
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/v1/datasets/ds1/chunks" in call_args[0][0]
        assert call_args[1]["json"]["document_ids"] == ["doc1", "doc2"]

    def test_retrieval(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0, "data": {"chunks": []}}
        mock_client.post.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        client.retrieval(
            dataset_ids=["ds1"],
            question="What is RAG?",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/v1/retrieval" in call_args[0][0]
        body = call_args[1]["json"]
        assert body["dataset_ids"] == ["ds1"]
        assert body["question"] == "What is RAG?"
        assert "similarity_threshold" in body
        assert "vector_similarity_weight" in body
        assert "top_k" in body


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_raises_on_http_error(self, monkeypatch, mock_client):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_client.get.return_value = mock_resp

        client = RagflowClient(tenant_id="tid", user_id="uid")
        with pytest.raises(httpx.HTTPStatusError):
            client.list_datasets()


# ---------------------------------------------------------------------------
# Public API helper
# ---------------------------------------------------------------------------


class TestGetRagflowClient:
    def test_get_ragflow_client_returns_instance(self, monkeypatch):
        monkeypatch.setenv("RAGFLOW_URL", "http://ragflow:9380")
        monkeypatch.setenv("RAGFLOW_SERVICE_KEY", "svc-key")
        from lfx.components.ragflow._client import RagflowClient, get_ragflow_client

        client = get_ragflow_client(
            tenant_id=_TEST_TENANT_UUID,
            user_id=_TEST_USER_UUID,
        )
        assert isinstance(client, RagflowClient)

"""RagflowClient HTTP helper for RAGFlow API integration.

Provides a synchronous HTTP client for Langflow components to interact with
RAGFlow's REST API. Reads configuration from environment variables set in
Docker Compose (Phase 5).

Usage from components::

    from lfx.components.ragflow._client import get_ragflow_client

    client = get_ragflow_client(
        tenant_id=self.ctx.get("tenant_id", ""),
        user_id=str(self.graph.user_id or ""),
    )
    datasets = client.list_datasets()
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# Module-level cached config (reset in tests via monkeypatch)
_RAGFLOW_URL: str | None = None
_RAGFLOW_SERVICE_KEY: str | None = None

_DEFAULT_RAGFLOW_URL = "http://ragflow:9380"
_DEFAULT_TIMEOUT = 30.0


def _get_ragflow_url() -> str:
    """Return the RAGFlow base URL, reading from env on first call."""
    global _RAGFLOW_URL  # noqa: PLW0603
    if _RAGFLOW_URL is None:
        _RAGFLOW_URL = os.environ.get("RAGFLOW_URL", _DEFAULT_RAGFLOW_URL)
    return _RAGFLOW_URL


def _get_service_key() -> str:
    """Return the service key, reading from env on first call."""
    global _RAGFLOW_SERVICE_KEY  # noqa: PLW0603
    if _RAGFLOW_SERVICE_KEY is None:
        _RAGFLOW_SERVICE_KEY = os.environ.get("RAGFLOW_SERVICE_KEY", "")
    return _RAGFLOW_SERVICE_KEY


def _strip_dashes(uuid_str: str) -> str:
    """Remove dashes from a UUID string to produce RAGFlow's 32-char hex format."""
    return uuid_str.replace("-", "")


class RagflowClient:
    """Synchronous HTTP client for RAGFlow API.

    Constructs the required service-auth headers (X-Service-Key, X-Tenant-ID,
    X-User-ID) for every request. Tenant and user IDs are dash-stripped to
    match RAGFlow's 32-character hex format.

    Args:
        tenant_id: Tenant UUID (dashes are stripped automatically).
        user_id: User UUID (dashes are stripped automatically).
    """

    def __init__(self, tenant_id: str, user_id: str) -> None:
        self.base_url = _get_ragflow_url()
        self._service_key = _get_service_key()
        self._tenant_id = _strip_dashes(tenant_id)
        self._user_id = _strip_dashes(user_id)

    @property
    def _headers(self) -> dict[str, str]:
        """Return headers required by RAGFlow's service_auth_required decorator."""
        return {
            "X-Service-Key": self._service_key,
            "X-Tenant-ID": self._tenant_id,
            "X-User-ID": self._user_id,
        }

    # ------------------------------------------------------------------
    # Dataset (Knowledge Base) operations
    # ------------------------------------------------------------------

    def list_datasets(self, page: int = 1, page_size: int = 30) -> dict[str, Any]:
        """List datasets (knowledge bases) for the current tenant.

        GET /api/v1/datasets?page={page}&page_size={page_size}
        """
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.get(
                f"{self.base_url}/api/v1/datasets",
                params={"page": page, "page_size": page_size},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    def create_dataset(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Create a new dataset (knowledge base).

        POST /api/v1/datasets  body: {"name": name, ...kwargs}
        """
        body: dict[str, Any] = {"name": name, **kwargs}
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.post(
                f"{self.base_url}/api/v1/datasets",
                json=body,
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    def delete_datasets(self, ids: list[str]) -> dict[str, Any]:
        """Delete one or more datasets by ID.

        DELETE /api/v1/datasets  body: {"ids": [...]}
        """
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.delete(
                f"{self.base_url}/api/v1/datasets",
                json={"ids": ids},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def upload_document(
        self,
        dataset_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> dict[str, Any]:
        """Upload a document to a dataset via multipart/form-data.

        POST /api/v1/datasets/{dataset_id}/documents
        """
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.post(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                files={"file": (filename, file_bytes)},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    def parse_documents(
        self,
        dataset_id: str,
        document_ids: list[str],
    ) -> dict[str, Any]:
        """Trigger document parsing (chunking) for the given documents.

        POST /api/v1/datasets/{dataset_id}/chunks  body: {"document_ids": [...]}
        """
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.post(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks",
                json={"document_ids": document_ids},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieval(
        self,
        dataset_ids: list[str],
        question: str,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
    ) -> dict[str, Any]:
        """Retrieve relevant chunks from datasets for a question.

        POST /api/v1/retrieval  body: {dataset_ids, question, ...}
        """
        body: dict[str, Any] = {
            "dataset_ids": dataset_ids,
            "question": question,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
        }
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as http:
            resp = http.post(
                f"{self.base_url}/api/v1/retrieval",
                json=body,
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()


def get_ragflow_client(tenant_id: str, user_id: str) -> RagflowClient:
    """Public factory for RagflowClient.

    Args:
        tenant_id: Tenant UUID (dashes stripped automatically).
        user_id: User UUID (dashes stripped automatically).

    Returns:
        Configured RagflowClient instance.
    """
    return RagflowClient(tenant_id=tenant_id, user_id=user_id)

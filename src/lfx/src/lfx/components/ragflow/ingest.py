"""RagflowIngestDocument component for Langflow.

Upload and process documents for deep parsing via RAGFlow's document
understanding engine. Supports PDF, DOCX, TXT, and other formats.

Usage in flows:
    1. Connect a file source to the Document File input
    2. Specify the Knowledge Base ID to ingest into
    3. The component uploads the file and triggers parsing automatically
"""

from __future__ import annotations

from pathlib import Path

import httpx

from lfx.base.data.storage_utils import read_file_bytes
from lfx.components.ragflow._client import get_ragflow_client
from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.utils.async_helpers import run_until_complete


class RagflowIngestDocument(Component):
    """Upload and process documents via RAGFlow's document understanding engine."""

    display_name = "RAGFlow Document Ingestion"
    description = (
        "Upload and process documents for deep parsing via RAGFlow's document "
        "understanding engine. Supports PDF, DOCX, TXT, and other formats."
    )
    icon = "file-up"
    name = "RagflowIngestDocument"  # STABLE -- never rename

    inputs = [
        MessageTextInput(
            name="dataset_id",
            display_name="Knowledge Base ID",
            required=True,
            info="The ID of the RAGFlow knowledge base to ingest documents into.",
        ),
        FileInput(
            name="file",
            display_name="Document File",
            required=True,
            info="The document file to upload and process.",
            file_types=["pdf", "docx", "txt", "md", "csv", "xlsx", "pptx"],
        ),
    ]

    outputs = [
        Output(display_name="JSON", name="result", method="ingest_document"),
    ]

    def ingest_document(self) -> Data:
        """Upload a document to RAGFlow and trigger parsing.

        Returns:
            Data object with document_ids, dataset_id, status, and filename.
        """
        try:
            # Resolve tenant and user identity
            tenant_id = self.graph.context.get("tenant_id") or str(self.user_id).replace("-", "")
            user_id = str(self.user_id).replace("-", "")

            # Create RAGFlow client
            client = get_ragflow_client(tenant_id, user_id)

            # Read file bytes via storage-compatible API (supports local + S3)
            resolved = self.resolve_path(self.file)
            file_bytes = run_until_complete(read_file_bytes(resolved))
            filename = Path(resolved).name

            # Upload document
            result = client.upload_document(self.dataset_id, file_bytes, filename)

            # Check RAGFlow response code
            if result.get("code") != 0:
                error_msg = result.get("message", "Upload failed")
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Extract document IDs
            doc_ids = [d["id"] for d in result.get("data", [])]

            # Trigger parsing
            client.parse_documents(self.dataset_id, doc_ids)

            # Set status and return result
            self.status = f"Uploaded {filename}, parsing started for {len(doc_ids)} document(s)"
            return Data(
                data={
                    "document_ids": doc_ids,
                    "dataset_id": self.dataset_id,
                    "status": "parsing_started",
                    "filename": filename,
                }
            )

        except httpx.HTTPStatusError as exc:
            error_message = f"Ingestion HTTP error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        except httpx.TimeoutException as exc:
            error_message = f"Ingestion timeout: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        except httpx.RequestError as exc:
            error_message = f"Ingestion request error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        except (OSError, ValueError, KeyError) as exc:
            error_message = f"Ingestion error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})

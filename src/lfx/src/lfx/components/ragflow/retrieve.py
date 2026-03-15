"""RagflowRetrieve component for Langflow.

Search and retrieve relevant document chunks from RAGFlow knowledge bases
using hybrid search (BM25 + dense vectors).

Usage in flows:
    1. Provide the search query and knowledge base IDs
    2. Optionally tune hybrid search parameters (top_k, thresholds, weights)
    3. Returns ranked document chunks as Table or JSON
"""

from __future__ import annotations

import httpx

from lfx.components.ragflow._client import get_ragflow_client
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, FloatInput, IntInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class RagflowRetrieve(Component):
    """Search and retrieve document chunks from RAGFlow knowledge bases."""

    display_name = "RAGFlow Retrieval"
    description = (
        "Search and retrieve relevant document chunks from RAGFlow knowledge "
        "bases using hybrid search (BM25 + dense vectors)."
    )
    icon = "search"
    name = "RagflowRetrieve"  # STABLE -- never rename

    inputs = [
        MessageTextInput(
            name="query",
            display_name="Search Query",
            required=True,
            tool_mode=True,
            info="The question or search query to find relevant document chunks.",
        ),
        MessageTextInput(
            name="dataset_ids",
            display_name="Knowledge Base IDs",
            required=True,
            info="Comma-separated list of knowledge base IDs to search.",
        ),
        IntInput(
            name="top_k",
            display_name="Top K Results",
            advanced=True,
            value=5,
            info="Maximum number of chunks to return.",
        ),
        FloatInput(
            name="similarity_threshold",
            display_name="Similarity Threshold",
            advanced=True,
            value=0.2,
            info="Minimum similarity score (0-1) for returned chunks.",
        ),
        FloatInput(
            name="vector_similarity_weight",
            display_name="Vector Weight",
            advanced=True,
            value=0.3,
            info="Weight of vector similarity vs keyword similarity (0=keyword only, 1=vector only).",
        ),
        BoolInput(
            name="highlight",
            display_name="Highlight Matches",
            advanced=True,
            value=True,
            info="Highlight matching terms in returned content.",
        ),
    ]

    outputs = [
        Output(display_name="Table", name="results_table", method="retrieve_table"),
        Output(display_name="JSON", name="results_json", method="retrieve_json"),
    ]

    def _do_retrieval(self) -> list[dict]:
        """Execute retrieval against RAGFlow and return raw chunk dicts.

        Returns:
            List of chunk dictionaries from RAGFlow response.

        Raises:
            httpx.HTTPStatusError: On HTTP-level errors.
            httpx.TimeoutException: On request timeout.
            httpx.RequestError: On connection errors.
        """
        # Resolve tenant and user identity
        tenant_id = self.graph.context.get("tenant_id") or str(self.user_id).replace("-", "")
        user_id = str(self.user_id).replace("-", "")

        # Create RAGFlow client
        client = get_ragflow_client(tenant_id, user_id)

        # Parse comma-separated dataset IDs
        ids = [id_str.strip() for id_str in self.dataset_ids.split(",")]

        # Execute retrieval
        result = client.retrieval(
            dataset_ids=ids,
            question=self.query,
            similarity_threshold=self.similarity_threshold,
            vector_similarity_weight=self.vector_similarity_weight,
            top_k=self.top_k,
        )

        # Check RAGFlow response code
        if result.get("code") != 0:
            error_msg = result.get("message", "Retrieval failed")
            self.status = error_msg
            return [{"_error": error_msg}]

        # Extract chunks
        return result.get("data", {}).get("chunks", [])

    def retrieve_json(self) -> list[Data]:
        """Retrieve chunks and return as list of Data objects.

        Returns:
            List of Data objects, each containing chunk content and metadata.
        """
        try:
            chunks = self._do_retrieval()

            # Handle error responses
            if len(chunks) == 1 and "_error" in chunks[0]:
                return [Data(data={"error": chunks[0]["_error"]})]

            # Map chunks to Data objects
            data_list = [
                Data(
                    text=chunk.get("content", ""),
                    data={
                        "content": chunk.get("content", ""),
                        "similarity": chunk.get("similarity", 0.0),
                        "doc_name": chunk.get("doc_name", ""),
                        "highlight": chunk.get("highlight", ""),
                        "chunk_id": chunk.get("id", ""),
                    },
                )
                for chunk in chunks
            ]

        except httpx.HTTPStatusError as exc:
            error_message = f"Retrieval HTTP error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return [Data(data={"error": str(exc)})]
        except httpx.TimeoutException as exc:
            error_message = f"Retrieval timeout: {exc}"
            logger.error(error_message)
            self.status = error_message
            return [Data(data={"error": str(exc)})]
        except httpx.RequestError as exc:
            error_message = f"Retrieval request error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return [Data(data={"error": str(exc)})]
        else:
            self.status = f"Retrieved {len(data_list)} chunk(s)"
            return data_list

    def retrieve_table(self) -> DataFrame:
        """Retrieve chunks and return as a DataFrame.

        Returns:
            DataFrame containing chunk results.
        """
        data_list = self.retrieve_json()
        return DataFrame(data_list)

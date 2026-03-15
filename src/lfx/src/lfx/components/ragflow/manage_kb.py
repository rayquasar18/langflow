"""RagflowManageKnowledgeBase component for Langflow.

Create, list, and delete RAGFlow knowledge bases within a tenant.
Knowledge bases store processed documents for semantic retrieval.

Usage in flows:
    1. Select the action (create, list, or delete)
    2. For create: provide a name for the new knowledge base
    3. For delete: provide comma-separated knowledge base IDs
    4. For list: optionally configure pagination
"""

from __future__ import annotations

import httpx

from lfx.components.ragflow._client import get_ragflow_client
from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, IntInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class RagflowManageKnowledgeBase(Component):
    """Create, list, and delete RAGFlow knowledge bases."""

    display_name = "RAGFlow Knowledge Base"
    description = (
        "Create, list, and delete RAGFlow knowledge bases within your tenant. "
        "Knowledge bases store processed documents for semantic retrieval."
    )
    icon = "database"
    name = "RagflowManageKnowledgeBase"  # STABLE -- never rename

    inputs = [
        DropdownInput(
            name="action",
            display_name="Action",
            required=True,
            options=["create", "list", "delete"],
            value="list",
            info="The knowledge base operation to perform.",
        ),
        MessageTextInput(
            name="kb_name",
            display_name="Knowledge Base Name",
            info="Name for the new knowledge base (required for 'create' action).",
        ),
        MessageTextInput(
            name="kb_ids",
            display_name="Knowledge Base IDs",
            info="Comma-separated list of knowledge base IDs to delete (required for 'delete' action).",
        ),
        IntInput(
            name="page",
            display_name="Page",
            advanced=True,
            value=1,
            info="Page number for list results.",
        ),
        IntInput(
            name="page_size",
            display_name="Page Size",
            advanced=True,
            value=30,
            info="Number of results per page.",
        ),
    ]

    outputs = [
        Output(display_name="JSON", name="result", method="manage_kb"),
        Output(display_name="Table", name="result_table", method="manage_kb_table"),
    ]

    def manage_kb(self) -> Data:
        """Execute the selected knowledge base operation.

        Returns:
            Data object with operation results.
        """
        try:
            # Validate inputs before creating client
            if self.action == "create" and not self.kb_name:
                self.status = "Knowledge base name is required for create action"
                return Data(data={"error": "Knowledge base name is required for create action"})

            if self.action == "delete" and not self.kb_ids:
                self.status = "Knowledge base IDs are required for delete action"
                return Data(data={"error": "Knowledge base IDs are required for delete action"})

            # Resolve tenant and user identity
            tenant_id = self.graph.context.get("tenant_id") or str(self.user_id).replace("-", "")
            user_id = str(self.user_id).replace("-", "")

            # Create RAGFlow client
            client = get_ragflow_client(tenant_id, user_id)

            # Execute action
            if self.action == "create":
                result = client.create_dataset(name=self.kb_name)
            elif self.action == "list":
                result = client.list_datasets(page=self.page, page_size=self.page_size)
            elif self.action == "delete":
                ids = [id_str.strip() for id_str in self.kb_ids.split(",")]
                result = client.delete_datasets(ids)
            else:
                self.status = f"Unknown action: {self.action}"
                return Data(data={"error": f"Unknown action: {self.action}"})

            # Check RAGFlow response code
            if result.get("code") != 0:
                error_msg = result.get("message", "Operation failed")
                self.status = error_msg
                return Data(data={"error": error_msg})

        except httpx.HTTPStatusError as exc:
            error_message = f"KB operation HTTP error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        except httpx.TimeoutException as exc:
            error_message = f"KB operation timeout: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        except httpx.RequestError as exc:
            error_message = f"KB operation request error: {exc}"
            logger.error(error_message)
            self.status = error_message
            return Data(data={"error": str(exc)})
        else:
            # Set status summary
            self.status = f"Action '{self.action}' completed successfully"
            return Data(data=result)

    def manage_kb_table(self) -> DataFrame:
        """Execute operation and return results as a DataFrame.

        Returns:
            DataFrame containing operation results.
        """
        data = self.manage_kb()
        return DataFrame([data])

"""RAGFlow component package for Langflow.

Provides three Langflow components for RAGFlow integration:
- RagflowIngestDocument: Upload and parse documents into a RAGFlow knowledge base
- RagflowRetrieve: Retrieve relevant chunks from RAGFlow datasets
- RagflowManageKnowledgeBase: Create, list, and delete RAGFlow knowledge bases

Uses lazy imports following the same pattern as files_and_knowledge/__init__.py.
Component implementations are in Plan 02; this module registers the class names
so Langflow's dynamic import system can discover them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.ragflow.ingest import RagflowIngestDocument
    from lfx.components.ragflow.manage_kb import RagflowManageKnowledgeBase
    from lfx.components.ragflow.retrieve import RagflowRetrieve

_dynamic_imports = {
    "RagflowIngestDocument": "ingest",
    "RagflowRetrieve": "retrieve",
    "RagflowManageKnowledgeBase": "manage_kb",
}

__all__ = [
    "RagflowIngestDocument",
    "RagflowManageKnowledgeBase",
    "RagflowRetrieve",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import ragflow components on attribute access."""
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)

"""Langflow ragflow module - forwards to lfx.components.ragflow.

This module provides backwards compatibility by forwarding all imports
to lfx.components.ragflow where the actual RAGFlow component classes live.

Import patterns that work via this redirect:
    from langflow.components.ragflow import RagflowIngestDocument
    from langflow.components.ragflow import RagflowRetrieve
    from langflow.components.ragflow import RagflowManageKnowledgeBase
    from langflow.components.ragflow.ingest import RagflowIngestDocument
    from langflow.components.ragflow.retrieve import RagflowRetrieve
    from langflow.components.ragflow.manage_kb import RagflowManageKnowledgeBase
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

from lfx.components.ragflow import __all__ as _lfx_all

__all__: list[str] = list(_lfx_all)

# Register redirected submodules in sys.modules for direct importlib.import_module() calls
# This allows imports like: import langflow.components.ragflow.ingest
_redirected_submodules = {
    "langflow.components.ragflow.ingest": "lfx.components.ragflow.ingest",
    "langflow.components.ragflow.retrieve": "lfx.components.ragflow.retrieve",
    "langflow.components.ragflow.manage_kb": "lfx.components.ragflow.manage_kb",
}

for old_path, new_path in _redirected_submodules.items():
    if old_path not in sys.modules:

        class _RedirectedModule:
            _module: types.ModuleType | None

            def __init__(self, target_path: str, original_path: str):
                self._target_path = target_path
                self._original_path = original_path
                self._module = None

            def __getattr__(self, name: str) -> Any:
                if self._module is None:
                    from importlib import import_module

                    self._module = import_module(self._target_path)
                    # Also register under the original path for future imports
                    sys.modules[self._original_path] = self._module
                return getattr(self._module, name)

            def __repr__(self) -> str:
                return f"<redirected module '{self._original_path}' -> '{self._target_path}'>"

        sys.modules[old_path] = _RedirectedModule(new_path, old_path)  # type: ignore[assignment]


def __getattr__(attr_name: str) -> Any:
    """Forward attribute access to lfx.components.ragflow."""
    # Handle submodule access for backwards compatibility
    if attr_name in ("ingest", "retrieve", "manage_kb"):
        from importlib import import_module

        result = import_module(f"lfx.components.ragflow.{attr_name}")
        globals()[attr_name] = result
        return result

    from lfx.components import ragflow

    return getattr(ragflow, attr_name)


def __dir__() -> list[str]:
    """Forward dir() to lfx.components.ragflow."""
    return list(__all__)

"""CI guard test: class name stability for ragflow components.

Tests verify that:
1. _dynamic_imports dict contains the three required class names (fast sanity check)
2. All three classes are actually importable by exact name
3. All classes inherit from Component
4. Component.name matches class name for serialization stability
5. ragflow is registered in lfx.components.__init__._dynamic_imports

DO NOT rename component classes -- they are stable identifiers in saved flows.
"""

from __future__ import annotations

REQUIRED_CLASS_NAMES = [
    "RagflowIngestDocument",
    "RagflowRetrieve",
    "RagflowManageKnowledgeBase",
]

EXPECTED_CLASS_NAMES = set(REQUIRED_CLASS_NAMES)


class TestClassNameStability:
    """Plan 01 scaffold tests: verify _dynamic_imports dict integrity."""

    def test_dynamic_imports_contains_all_class_names(self):
        from lfx.components.ragflow import _dynamic_imports

        for name in EXPECTED_CLASS_NAMES:
            assert name in _dynamic_imports, (
                f"Missing class '{name}' in lfx.components.ragflow._dynamic_imports. "
                "Component class names are stable identifiers used in saved flows."
            )

    def test_dynamic_imports_values_are_module_names(self):
        from lfx.components.ragflow import _dynamic_imports

        expected_mapping = {
            "RagflowIngestDocument": "ingest",
            "RagflowRetrieve": "retrieve",
            "RagflowManageKnowledgeBase": "manage_kb",
        }
        for class_name, module_name in expected_mapping.items():
            assert _dynamic_imports[class_name] == module_name, (
                f"Class '{class_name}' should map to module '{module_name}', got '{_dynamic_imports.get(class_name)}'"
            )


class TestRagflowRegistration:
    """Verify ragflow package is registered in the main components init."""

    def test_ragflow_registered_in_components_init(self):
        from lfx.components import _dynamic_imports

        assert "ragflow" in _dynamic_imports, (
            "ragflow module must be registered in lfx.components.__init__._dynamic_imports"
        )
        assert _dynamic_imports["ragflow"] == "__module__", "ragflow entry should have value '__module__'"

    def test_ragflow_in_components_all(self):
        from lfx.components import __all__

        assert "ragflow" in __all__, "ragflow must be listed in lfx.components.__all__"


class TestActualClassImports:
    """Plan 03 upgraded tests: verify actual class imports and inheritance."""

    def test_all_ragflow_classes_importable(self):
        """NODE-04: All three RAGFlow component classes must be importable by exact name.

        DO NOT rename these classes -- they are stable identifiers in saved flows.
        """
        from lfx.components import ragflow

        for name in REQUIRED_CLASS_NAMES:
            cls = getattr(ragflow, name, None)
            assert cls is not None, (
                f"Class {name} not found in lfx.components.ragflow -- DO NOT rename component classes"
            )

    def test_ragflow_classes_inherit_from_component(self):
        """All RAGFlow components must inherit from Component."""
        from lfx.components.ragflow import (
            RagflowIngestDocument,
            RagflowManageKnowledgeBase,
            RagflowRetrieve,
        )
        from lfx.custom.custom_component.component import Component

        for cls in [RagflowIngestDocument, RagflowRetrieve, RagflowManageKnowledgeBase]:
            assert issubclass(cls, Component), f"{cls.__name__} does not inherit from Component"

    def test_ragflow_class_name_matches_name_attribute(self):
        """Component.name must match the class name for serialization stability."""
        from lfx.components.ragflow import (
            RagflowIngestDocument,
            RagflowManageKnowledgeBase,
            RagflowRetrieve,
        )

        for cls in [RagflowIngestDocument, RagflowRetrieve, RagflowManageKnowledgeBase]:
            assert cls.name == cls.__name__, f"{cls.__name__}.name is '{cls.name}' but must be '{cls.__name__}'"

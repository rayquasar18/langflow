"""CI guard test: class name stability for ragflow components.

Scaffold level -- checks that _dynamic_imports dict contains the
three required class names and that ragflow is registered in
lfx.components.__init__._dynamic_imports.

Plan 03 upgrades this to actual class import tests after
Plan 02 creates the component implementations.
"""

from __future__ import annotations

EXPECTED_CLASS_NAMES = {
    "RagflowIngestDocument",
    "RagflowRetrieve",
    "RagflowManageKnowledgeBase",
}


class TestClassNameStability:
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
    def test_ragflow_registered_in_components_init(self):
        from lfx.components import _dynamic_imports

        assert "ragflow" in _dynamic_imports, (
            "ragflow module must be registered in lfx.components.__init__._dynamic_imports"
        )
        assert _dynamic_imports["ragflow"] == "__module__", "ragflow entry should have value '__module__'"

    def test_ragflow_in_components_all(self):
        from lfx.components import __all__

        assert "ragflow" in __all__, "ragflow must be listed in lfx.components.__all__"

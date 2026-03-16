"""Unit tests for quota enforcement and feature gating.

Tests the pure functions and data structures from langflow.middleware.quota:
- filter_components_by_tier: Component filtering for each tier
- get_tier_config: Tier configuration lookup
- TIER_DEFINITIONS: Structure validation
- TIER_GATED_COMPONENTS: Mapping validation
"""

from __future__ import annotations

import pytest
from langflow.middleware.quota import (
    TIER_DEFINITIONS,
    TIER_GATED_COMPONENTS,
    filter_components_by_tier,
    get_tier_config,
)

# ---------------------------------------------------------------------------
# Sample component types dict for testing
# ---------------------------------------------------------------------------


def _make_all_types() -> dict:
    """Create a sample all_types dict mimicking the real component cache."""
    return {
        "RAG": {
            "RagflowIngestDocument": {"display_name": "Ingest Document", "type": "component"},
            "RagflowRetrieve": {"display_name": "RAG Retrieve", "type": "component"},
            "RagflowManageKnowledgeBase": {"display_name": "Manage KB", "type": "component"},
        },
        "Custom": {
            "CustomComponent": {"display_name": "Custom Code", "type": "component"},
            "PythonFunction": {"display_name": "Python Function", "type": "component"},
        },
        "Chat": {
            "ChatInput": {"display_name": "Chat Input", "type": "component"},
            "ChatOutput": {"display_name": "Chat Output", "type": "component"},
        },
    }


# ---------------------------------------------------------------------------
# filter_components_by_tier tests
# ---------------------------------------------------------------------------


class TestFilterComponentsByTier:
    def test_free_tier_removes_ragflow_ingest(self):
        """Free tier should not see RagflowIngestDocument (requires advanced_rag)."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "free")

        # RagflowIngestDocument should be removed
        assert "RagflowIngestDocument" not in result.get("RAG", {})
        # RagflowRetrieve should remain (basic_rag)
        assert "RagflowRetrieve" in result.get("RAG", {})
        # RagflowManageKnowledgeBase should remain (basic_rag)
        assert "RagflowManageKnowledgeBase" in result.get("RAG", {})

    def test_free_tier_removes_custom_component(self):
        """Free tier should not see CustomComponent (requires custom_components)."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "free")

        assert "CustomComponent" not in result.get("Custom", {})
        # PythonFunction is not gated
        assert "PythonFunction" in result.get("Custom", {})

    def test_free_tier_keeps_chat_components(self):
        """Free tier should see all basic (ungated) components."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "free")

        assert "ChatInput" in result["Chat"]
        assert "ChatOutput" in result["Chat"]

    def test_pro_tier_keeps_all_components(self):
        """Pro tier has advanced_rag and custom_components, so sees everything."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "pro")

        assert "RagflowIngestDocument" in result["RAG"]
        assert "RagflowRetrieve" in result["RAG"]
        assert "CustomComponent" in result["Custom"]
        assert "ChatInput" in result["Chat"]

    def test_enterprise_tier_keeps_all_components(self):
        """Enterprise tier has all features, sees everything."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "enterprise")

        assert "RagflowIngestDocument" in result["RAG"]
        assert "RagflowRetrieve" in result["RAG"]
        assert "CustomComponent" in result["Custom"]
        assert "ChatInput" in result["Chat"]

    def test_empty_categories_removed(self):
        """If filtering removes all components from a category, that category is excluded."""
        all_types = {
            "OnlyGated": {
                "RagflowIngestDocument": {"type": "component"},
            },
            "Mixed": {
                "RagflowIngestDocument": {"type": "component"},
                "ChatInput": {"type": "component"},
            },
        }
        result = filter_components_by_tier(all_types, "free")

        # OnlyGated had only RagflowIngestDocument; should be removed entirely
        assert "OnlyGated" not in result
        # Mixed should still exist with ChatInput
        assert "Mixed" in result
        assert "ChatInput" in result["Mixed"]
        assert "RagflowIngestDocument" not in result["Mixed"]

    def test_non_dict_categories_pass_through(self):
        """Non-dict entries (e.g., metadata) should pass through unchanged."""
        all_types = {
            "_metadata": "some-value",
            "RAG": {
                "RagflowIngestDocument": {"type": "component"},
                "RagflowRetrieve": {"type": "component"},
            },
        }
        result = filter_components_by_tier(all_types, "free")
        assert result["_metadata"] == "some-value"

    def test_unknown_tier_defaults_to_free(self):
        """Unknown tier names should default to free tier behavior."""
        all_types = _make_all_types()
        result = filter_components_by_tier(all_types, "nonexistent_tier")

        # Should behave like free tier
        assert "RagflowIngestDocument" not in result.get("RAG", {})
        assert "RagflowRetrieve" in result.get("RAG", {})

    def test_does_not_mutate_input(self):
        """filter_components_by_tier should not modify the input dict."""
        all_types = _make_all_types()
        original_rag_keys = set(all_types["RAG"].keys())
        filter_components_by_tier(all_types, "free")
        assert set(all_types["RAG"].keys()) == original_rag_keys


# ---------------------------------------------------------------------------
# get_tier_config tests
# ---------------------------------------------------------------------------


class TestGetTierConfig:
    def test_free_tier_quotas(self):
        cfg = get_tier_config("free")
        assert cfg["quotas"]["max_flows"] == 5
        assert cfg["quotas"]["max_kb_docs"] == 50
        assert cfg["quotas"]["max_requests_per_minute"] == 20

    def test_pro_tier_quotas(self):
        cfg = get_tier_config("pro")
        assert cfg["quotas"]["max_flows"] == 50
        assert cfg["quotas"]["max_kb_docs"] == 500
        assert cfg["quotas"]["max_requests_per_minute"] == 100

    def test_enterprise_tier_unlimited(self):
        cfg = get_tier_config("enterprise")
        assert cfg["quotas"]["max_flows"] == -1
        assert cfg["quotas"]["max_kb_docs"] == -1
        assert cfg["quotas"]["max_requests_per_minute"] == -1

    def test_unknown_tier_defaults_to_free(self):
        cfg = get_tier_config("unknown")
        assert cfg == TIER_DEFINITIONS["free"]

    def test_free_tier_features(self):
        cfg = get_tier_config("free")
        assert "basic_rag" in cfg["features"]
        assert "basic_flows" in cfg["features"]
        assert "advanced_rag" not in cfg["features"]
        assert "custom_components" not in cfg["features"]

    def test_pro_tier_features(self):
        cfg = get_tier_config("pro")
        assert "advanced_rag" in cfg["features"]
        assert "custom_components" in cfg["features"]
        assert "graphrag" not in cfg["features"]

    def test_enterprise_tier_features(self):
        cfg = get_tier_config("enterprise")
        assert "advanced_rag" in cfg["features"]
        assert "custom_components" in cfg["features"]
        assert "graphrag" in cfg["features"]


# ---------------------------------------------------------------------------
# TIER_GATED_COMPONENTS tests
# ---------------------------------------------------------------------------


class TestTierGatedComponents:
    def test_advanced_rag_gates_ingest(self):
        assert "RagflowIngestDocument" in TIER_GATED_COMPONENTS["advanced_rag"]

    def test_custom_components_gates_custom(self):
        assert "CustomComponent" in TIER_GATED_COMPONENTS["custom_components"]

    def test_graphrag_is_empty_placeholder(self):
        assert TIER_GATED_COMPONENTS["graphrag"] == set()

    def test_all_values_are_sets(self):
        for feature, components in TIER_GATED_COMPONENTS.items():
            assert isinstance(components, set), f"{feature} should map to a set"

    def test_features_are_strings(self):
        for feature in TIER_GATED_COMPONENTS:
            assert isinstance(feature, str)


# ---------------------------------------------------------------------------
# TIER_DEFINITIONS structure tests
# ---------------------------------------------------------------------------


class TestTierDefinitions:
    @pytest.mark.parametrize("tier", ["free", "pro", "enterprise"])
    def test_tier_has_required_keys(self, tier: str):
        cfg = TIER_DEFINITIONS[tier]
        assert "display_name" in cfg
        assert "quotas" in cfg
        assert "features" in cfg

    @pytest.mark.parametrize("tier", ["free", "pro", "enterprise"])
    def test_tier_quotas_have_required_keys(self, tier: str):
        quotas = TIER_DEFINITIONS[tier]["quotas"]
        assert "max_flows" in quotas
        assert "max_kb_docs" in quotas
        assert "max_requests_per_minute" in quotas

    @pytest.mark.parametrize("tier", ["free", "pro", "enterprise"])
    def test_features_are_sets(self, tier: str):
        features = TIER_DEFINITIONS[tier]["features"]
        assert isinstance(features, set)

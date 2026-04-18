"""Phase 1: Node schema completeness regression tests.

Guards the baseline that every registered node type exposes a resolved schema
with descriptions filled in for every port and config field (both locales).

This is what the AI chatbot reads first — any regression (missing i18n key,
description, etc.) must fail loudly.
"""

from __future__ import annotations

from typing import List

import pytest

from programgarden_core import NodeTypeRegistry
from programgarden_core.i18n import translate_schema

try:
    import programgarden_community  # noqa: F401

    _COMMUNITY_AVAILABLE = True
except ImportError:
    _COMMUNITY_AVAILABLE = False


CORE_NODE_COUNT = 69
COMMUNITY_NODE_COUNT = 4
EXPECTED_TOTAL = CORE_NODE_COUNT + (COMMUNITY_NODE_COUNT if _COMMUNITY_AVAILABLE else 0)


def _all_types() -> List[str]:
    registry = NodeTypeRegistry()
    return sorted(registry.list_types())


def test_registry_node_count():
    """Registered node count must match the documented baseline."""
    types = _all_types()
    assert len(types) == EXPECTED_TOTAL, (
        f"expected {EXPECTED_TOTAL} nodes ({CORE_NODE_COUNT} core + "
        f"{COMMUNITY_NODE_COUNT if _COMMUNITY_AVAILABLE else 0} community), got {len(types)}: "
        f"{types}"
    )


@pytest.mark.parametrize("node_type", _all_types())
@pytest.mark.parametrize("locale", ["en", "ko"])
def test_schema_top_level_description_resolved(node_type: str, locale: str):
    """Each node schema must have a non-empty, i18n-resolved description."""
    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type, locale=locale)
    assert schema is not None, f"{node_type}: schema not registered"
    assert schema.description, f"{node_type} [{locale}]: description missing"
    assert not schema.description.startswith("i18n:"), (
        f"{node_type} [{locale}]: description has unresolved i18n key: {schema.description}"
    )


@pytest.mark.parametrize("node_type", _all_types())
@pytest.mark.parametrize("locale", ["en", "ko"])
def test_schema_display_name_resolved(node_type: str, locale: str):
    """Each node schema must have a resolved display_name (non-i18n prefix)."""
    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type, locale=locale)
    assert schema is not None
    assert schema.display_name, f"{node_type} [{locale}]: display_name missing"
    assert not schema.display_name.startswith("i18n:"), (
        f"{node_type} [{locale}]: display_name has unresolved i18n key: {schema.display_name}"
    )


@pytest.mark.parametrize("node_type", _all_types())
@pytest.mark.parametrize("locale", ["en", "ko"])
def test_schema_ports_have_descriptions(node_type: str, locale: str):
    """Every input/output port must expose a resolved description."""
    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type, locale=locale)
    assert schema is not None

    for port in schema.inputs + schema.outputs:
        port_name = port.get("name")
        desc = port.get("description")
        assert desc, f"{node_type}.{port_name} [{locale}]: port description missing"
        assert not desc.startswith("i18n:"), (
            f"{node_type}.{port_name} [{locale}]: port description has "
            f"unresolved i18n key: {desc}"
        )


@pytest.mark.parametrize("node_type", _all_types())
@pytest.mark.parametrize("locale", ["en", "ko"])
def test_schema_config_fields_have_descriptions(node_type: str, locale: str):
    """Every config_schema entry must expose a resolved description."""
    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type, locale=locale)
    assert schema is not None

    for fname, fmeta in schema.config_schema.items():
        if not isinstance(fmeta, dict):
            continue
        desc = fmeta.get("description")
        assert desc, (
            f"{node_type}.{fname} [{locale}]: config field description missing"
        )
        assert not desc.startswith("i18n:"), (
            f"{node_type}.{fname} [{locale}]: config field description has "
            f"unresolved i18n key: {desc}"
        )


@pytest.mark.parametrize("node_type", _all_types())
def test_schema_has_required_metadata(node_type: str):
    """Each schema must expose category / product_scope / broker_provider."""
    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type)
    assert schema is not None
    assert schema.category, f"{node_type}: category missing"
    assert schema.product_scope, f"{node_type}: product_scope missing"
    assert schema.broker_provider, f"{node_type}: broker_provider missing"
    assert schema.img_url, f"{node_type}: img_url missing"


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_translate_schema_does_not_fail_on_any_node(locale: str):
    """Sanity: translate_schema() must not raise for any registered node."""
    registry = NodeTypeRegistry()
    for node_type in _all_types():
        schema = registry.get_schema(node_type)
        assert schema is not None
        translated = translate_schema(schema.model_dump(), locale=locale)
        assert "description" in translated

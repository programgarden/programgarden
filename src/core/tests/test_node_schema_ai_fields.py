"""Phase 2: Node AI metadata shape + coverage tests.

AI-facing metadata is declared on each node class as five flat ClassVars
mirroring the existing `_img_url` / `_connection_rules` / `_rate_limit`
pattern:

    _usage: ClassVar[Dict[str, Any]]
    _features: ClassVar[List[str]]
    _anti_patterns: ClassVar[List[Dict[str, str]]]
    _examples: ClassVar[List[Dict[str, Any]]]
    _node_guide: ClassVar[Dict[str, Any]]

All values are English only and feed the workflow-generation AI chatbot
directly. Shape tests run over whatever nodes currently declare the
metadata; the coverage floor (`MIN_FILLED_NODES`) guards against
regression while the fill-in is in flight. Bump the floor when more
nodes land.
"""

from __future__ import annotations

from typing import List

import pytest

from programgarden_core import NodeTypeRegistry

try:
    import programgarden_community  # noqa: F401

    _COMMUNITY_AVAILABLE = True
except ImportError:
    _COMMUNITY_AVAILABLE = False


TARGET_NODE_COUNT = 73


def _all_types() -> List[str]:
    return sorted(NodeTypeRegistry().list_types())


def _filled_types() -> List[str]:
    """Node types whose schema has the 5 AI fields populated."""
    registry = NodeTypeRegistry()
    return sorted(
        t for t in registry.list_types()
        if (schema := registry.get_schema(t)) is not None
        and schema.usage is not None
    )


# ---------------------------------------------------------------------------
# Shape tests — run over whatever nodes currently declare metadata
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("node_type", _filled_types(), ids=lambda t: t)
def test_metadata_has_required_shape(node_type: str):
    """Every node that declares `_ai_metadata` must cover all 5 fields."""
    schema = NodeTypeRegistry().get_schema(node_type)
    assert schema is not None

    assert schema.usage is not None, f"{node_type}: usage missing"
    for key in ("when_to_use", "when_not_to_use", "typical_scenarios"):
        value = schema.usage.get(key)
        assert value, f"{node_type}: usage.{key} missing or empty"
        assert isinstance(value, list)

    assert schema.features and isinstance(schema.features, list), (
        f"{node_type}: features must be a non-empty list"
    )
    assert len(schema.features) >= 2, (
        f"{node_type}: features should list at least 2 bullets"
    )

    assert schema.anti_patterns is not None and isinstance(
        schema.anti_patterns, list
    ), f"{node_type}: anti_patterns must be a list"
    for ap in schema.anti_patterns:
        for key in ("pattern", "reason", "alternative"):
            assert ap.get(key), f"{node_type}: anti_patterns.{key} missing"

    assert schema.examples and isinstance(schema.examples, list), (
        f"{node_type}: examples must be a non-empty list"
    )
    assert len(schema.examples) >= 2, (
        f"{node_type}: examples must contain at least 2 entries"
    )
    for ex in schema.examples:
        for key in ("title", "description", "workflow_snippet", "expected_output"):
            assert key in ex, f"{node_type}: example missing '{key}'"
        wf = ex["workflow_snippet"]
        assert isinstance(wf, dict)
        assert "nodes" in wf and "edges" in wf

    assert schema.node_guide is not None and isinstance(schema.node_guide, dict)
    for key in ("input_handling", "output_consumption", "common_combinations", "pitfalls"):
        value = schema.node_guide.get(key)
        assert value, f"{node_type}: node_guide.{key} missing or empty"


@pytest.mark.parametrize("node_type", _filled_types(), ids=lambda t: t)
def test_metadata_workflow_snippets_validate(node_type: str):
    """Each example's workflow_snippet must pass WorkflowExecutor.validate().

    Skipped when `programgarden` package is not importable (core-only
    environment). The snippets themselves must remain executable.
    """
    try:
        from programgarden import WorkflowExecutor
    except ImportError:
        pytest.skip("programgarden package not available in this environment")

    schema = NodeTypeRegistry().get_schema(node_type)
    assert schema is not None
    executor = WorkflowExecutor()
    for ex in schema.examples or []:
        result = executor.validate(ex["workflow_snippet"])
        assert result.is_valid, (
            f"{node_type} example {ex['title'][:40]!r}: "
            f"{[str(e) for e in result.errors[:3]]}"
        )


# ---------------------------------------------------------------------------
# Coverage tracking — surfaces fill-in progress
# ---------------------------------------------------------------------------


def test_metadata_coverage_full():
    """Every registered node must declare `_ai_metadata`.

    Phase 2 fill-in is complete; any new node class must add the 5 AI
    ClassVars at introduction time.
    """
    filled = set(_filled_types())
    registered = set(_all_types())
    missing = sorted(registered - filled)
    assert not missing, f"{len(missing)} nodes missing _ai_metadata: {missing}"
    assert len(registered) >= TARGET_NODE_COUNT or not _COMMUNITY_AVAILABLE, (
        f"expected at least {TARGET_NODE_COUNT} registered nodes "
        f"(community available={_COMMUNITY_AVAILABLE}), got {len(registered)}"
    )


def test_metadata_coverage_snapshot(capsys):
    """Emit a snapshot so progress is legible when running the suite."""
    filled = set(_filled_types())
    registered = set(_all_types())
    missing = sorted(registered - filled)
    print(
        f"\n[AI metadata coverage] {len(filled)}/{len(registered)} "
        f"filled; first missing: {missing[:5]}"
    )
    assert len(registered) >= TARGET_NODE_COUNT or not _COMMUNITY_AVAILABLE

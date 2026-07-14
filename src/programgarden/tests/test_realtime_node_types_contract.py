"""REALTIME_NODE_TYPES must cover every node that declares `stay_connected`.

Why this test exists
--------------------
Three separate lifecycle decisions key off the realtime node-type set:

  1. `_find_stay_connected_nodes` — does the job enter the event loop? If not, the
     job completes as soon as the main flow ends and the `finally` block calls
     `cleanup_persistent_nodes()`, which sets the shutdown flag and CLOSES the
     WebSocket. Ticks then never arrive.
  2. `_get_trigger_nodes` — does the node auto-trigger its downstream chain on
     each event?
  3. re-execution — is the node skipped when already running (loop prevention)?

That set was copy-pasted at all three sites. The Korea family
(`KoreaStockReal*Node`), added later, was never added to any of them — so Korea
realtime workflows had no event source at all: the job finished in ~2s, the
socket was torn down, and zero ticks ever reached the table. The library itself
was streaming ~1000 ticks/45s the whole time.

The list is now a single constant, and this test makes the DECLARATIONS the
source of truth: declare `stay_connected` on a node and you are in the set, or
this test fails. A hand-maintained list drifts; a derived one cannot.
"""
import pytest

from programgarden.executor import REALTIME_NODE_TYPES, WorkflowExecutor
from programgarden_core.registry.node_registry import NodeTypeRegistry


# Nodes that declare `stay_connected` but are deliberately NOT event sources.
# MarketStatusNode holds a JIF subscription with its own lifecycle
# (`_cleanup_jif_subscriptions`) and must not keep the job alive on its own.
_NOT_EVENT_SOURCES = {"MarketStatusNode"}


def _declares_stay_connected(cls) -> bool:
    for attr in ("get_field_schema", "get_config_schema"):
        fn = getattr(cls, attr, None)
        if not callable(fn):
            continue
        try:
            schema = fn()
        except Exception:
            continue
        if isinstance(schema, dict):
            if "stay_connected" in schema:
                return True
            props = schema.get("properties")
            if isinstance(props, dict) and "stay_connected" in props:
                return True
        elif isinstance(schema, (list, tuple)):
            for f in schema:
                name = getattr(f, "name", None) or (
                    f.get("name") if isinstance(f, dict) else None
                )
                if name == "stay_connected":
                    return True
    return False


def _nodes_declaring_stay_connected():
    reg = NodeTypeRegistry()
    found = set()
    for nt in reg.list_types():
        try:
            cls = reg.get(nt)
        except Exception:
            continue
        if cls is not None and _declares_stay_connected(cls):
            found.add(nt)
    return found


def test_realtime_node_types_cover_declarations():
    """Every node declaring `stay_connected` is an event source (or explicitly exempt).

    This is the guard that would have caught the dead Korea realtime family.
    """
    declared = _nodes_declaring_stay_connected()
    assert declared, "no node declares stay_connected — registry introspection broke"

    missing = declared - REALTIME_NODE_TYPES - _NOT_EVENT_SOURCES
    assert not missing, (
        f"{sorted(missing)} declare `stay_connected` but are absent from "
        f"REALTIME_NODE_TYPES. Such a node never keeps the job alive, so its "
        f"WebSocket is torn down when the main flow ends and it silently "
        f"delivers zero events. Add it to REALTIME_NODE_TYPES (or to "
        f"_NOT_EVENT_SOURCES with a reason)."
    )


def test_realtime_node_types_are_real_nodes():
    """No stale entries: every listed type is something the engine can actually run.

    Checked against the executor map as well as the declaration registry: the
    generic `Real*Node` names are executable legacy aliases that the registry does
    not declare, so registry membership alone would false-fail on them.
    """
    reg = NodeTypeRegistry()
    known = set(reg.list_types()) | set(WorkflowExecutor()._executors)
    stale = {nt for nt in REALTIME_NODE_TYPES if nt not in known}
    assert not stale, f"REALTIME_NODE_TYPES lists unknown node types: {sorted(stale)}"


@pytest.mark.parametrize(
    "node_type",
    ["KoreaStockRealMarketDataNode", "KoreaStockRealAccountNode",
     "KoreaStockRealOrderEventNode"],
)
def test_korea_realtime_family_is_an_event_source(node_type):
    """Regression: the Korea family was missing from all three lifecycle lists."""
    assert node_type in REALTIME_NODE_TYPES

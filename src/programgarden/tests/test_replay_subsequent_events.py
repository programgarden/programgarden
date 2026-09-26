"""Unsupported recorded event types name the type and the node's emittable set.

A `duplicate` (subsequent-event) scenario is only applicable to a recurring
trigger. When a suite attaches an `events` frame to a workflow whose trigger is a
manual StartNode (or any one-shot node), replay now names the recorded event type,
the node's emittable types, and that a subsequent event requires a recurring
trigger node — a suite specification defect, not a node defect. The
`subsequent_event_types` helper (which the gate itself uses) lets the AI-side
suite compiler decide applicability up front.
"""
import pytest

from programgarden.replay_events import subsequent_event_types
from programgarden.replay_triggers import subsequent_event_types as via_triggers
from programgarden.validation_replay import replay
from tests.test_replay_events import counter
from tests.test_validation_replay import code, workflow

AS_OF = "2026-09-22T14:00:00Z"
# Mirrors the enum in replay_events.checked_events.
EVENT_ENUM = {"schedule_tick", "realtime_update", "market_data", "order_event"}


def test_helper_is_re_exported_from_replay_triggers():
    assert via_triggers is subsequent_event_types


@pytest.mark.parametrize("node_type,expected", [
    ("StartNode", set()),
    ("TradingHoursFilterNode", set()),
    ("SQLiteNode", set()),
    ("CodeNode", set()),
    ("OverseasStockMarketDataNode", set()),  # one-shot REST snapshot, not a stream
    ("ScheduleNode", {"schedule_tick"}),
    ("OverseasStockRealMarketDataNode", {"market_data", "realtime_update"}),
    ("KoreaStockRealMarketDataNode", {"market_data", "realtime_update"}),
    ("OverseasFuturesRealMarketDataNode", {"market_data", "realtime_update"}),
    ("OverseasStockRealOrderEventNode", {"order_event", "realtime_update"}),
    ("KoreaStockRealOrderEventNode", {"order_event", "realtime_update"}),
    ("OverseasFuturesRealOrderEventNode", {"order_event", "realtime_update"}),
    ("OverseasStockRealAccountNode", {"realtime_update"}),
    ("KoreaStockRealAccountNode", {"realtime_update"}),
    ("OverseasFuturesRealAccountNode", {"realtime_update"}),
])
def test_subsequent_event_types_sets(node_type, expected):
    assert subsequent_event_types(node_type) == frozenset(expected)


def test_helper_matches_the_node_catalog_and_event_contract():
    # Ground the helper against the actual registry and the recorded-events enum:
    # non-empty for exactly ScheduleNode plus the three realtime stream families,
    # and every emittable type is a real recorded-event type.
    from programgarden.executor import WorkflowExecutor
    from programgarden_core import NodeTypeRegistry
    WorkflowExecutor()
    types = NodeTypeRegistry().list_types()
    emitting = {t for t in types if subsequent_event_types(t)}
    expected = {t for t in types if t == "ScheduleNode"
                or t.endswith(("RealMarketDataNode", "RealOrderEventNode", "RealAccountNode"))}
    assert emitting == expected
    assert "ScheduleNode" in emitting and any(t.endswith("RealMarketDataNode") for t in emitting)
    for node_type in types:
        assert subsequent_event_types(node_type) <= EVENT_ENUM


@pytest.mark.asyncio
async def test_startnode_subsequent_event_is_named_as_a_spec_defect():
    # The exact reported case: a StartNode-only workflow with a subsequent event.
    graph = workflow(code("calc", "1"))
    fixture = {"as_of": AS_OF, "events": [
        {"as_of": "2026-09-22T14:05:00Z", "type": "realtime_update", "source_node_id": "start"}]}
    result = await replay(graph, fixture)
    assert not result.passed
    err = next(e for e in result.errors if e.get("detail", {}).get("recorded_event_type"))
    assert err["code"] == "REPLAY_CONTRACT_FAILED" and err["path"] == "start"
    detail = err["detail"]
    assert detail["recorded_event_type"] == "realtime_update"
    assert detail["node_type"] == "StartNode"
    assert detail["emittable_event_types"] == []
    assert "recurring trigger" in detail["hint"] and "StartNode" in detail["hint"]
    assert "StartNode" in err["message"] and "realtime_update" in err["message"]
    assert "recurring trigger" in err["message"] and "cannot emit" in err["message"]


@pytest.mark.asyncio
async def test_non_stream_node_event_names_type_and_empty_emittable_set():
    # A SQLite node cannot be a subsequent-event source; the detail names it.
    graph, fixture = counter()
    fixture["events"][0]["source_node_id"] = "count"  # a SQLiteNode
    result = await replay(graph, fixture)
    assert not result.passed
    err = next(e for e in result.errors if e.get("detail", {}).get("recorded_event_type"))
    assert err["detail"]["node_type"] == "SQLiteNode"
    assert err["detail"]["emittable_event_types"] == []
    assert err["detail"]["recorded_event_type"] == "schedule_tick"
    assert "cannot emit" in err["message"]


@pytest.mark.asyncio
async def test_schedule_tick_is_accepted_for_a_recurring_schedule_source():
    # Positive replay behavior for the one non-empty set reachable without broker
    # fixtures: a ScheduleNode source emits schedule_tick events end to end.
    graph, fixture = counter()
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert [e["type"] for e in result.events] == ["schedule_tick", "schedule_tick"]
    assert subsequent_event_types("ScheduleNode") == frozenset({"schedule_tick"})

"""A recorded open-orders/completion snapshot must be well formed at its own node.

Regression for the paid-probe defect where a malformed ``*OpenOrdersNode``
recording (a row with only ``symbol`` and no ``order_id``) passed while the
node was validated alone and only failed once an order node created a simulated
book, blaming the innocent downstream order node. The snapshot SHAPE now runs
unconditionally at the recorded node itself.
"""
import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_external import recording
from programgarden.replay_order_adapter import (
    check_open_orders_snapshot, check_order_events_shape, open_orders_snapshot_contract)
from programgarden.validation_replay import replay
from tests.test_replay_order_adapter import case, AS_OF


def open_orders_graph(rows, count=None):
    """start -> broker -> OpenOrdersNode, with NO order node (so no book is seeded)."""
    graph, fixture = case()
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "order"]
    graph["nodes"].append({"id": "observed", "type": "OverseasStockOpenOrdersNode"})
    graph["edges"] = [{"from": "start", "to": "broker"}, {"from": "broker", "to": "observed"}]
    fixture.pop("orders", None)
    output = {"open_orders": rows, "count": len(rows) if count is None else count}
    fixture["nodes"]["observed"] = recording(
        "OverseasStockOpenOrdersNode",
        {"connection": fixture["nodes"]["broker"]["output"]["connection"]},
        output, {"type": "object", "required": ["open_orders", "count"]}, as_of=AS_OF)
    return graph, fixture


@pytest.mark.asyncio
async def test_malformed_open_orders_recording_fails_at_its_node_without_an_order_node():
    # Row omits order_id. Historically self.orders was None here (no order node),
    # so the shape check was skipped and the defect only surfaced once an order
    # node joined the chain. It must now fail at the OpenOrdersNode itself.
    graph, fixture = open_orders_graph([{"symbol": "A"}])
    result = await replay(graph, fixture)
    assert not result.passed
    failure = next(e for e in result.errors if e.get("node_id") == "observed")
    assert failure["code"] == "REPLAY_CONTRACT_FAILED", result.errors
    assert failure["path"] == "open_orders.open_orders[0].order_id"
    assert failure["detail"]["present_keys"] == ["symbol"]


@pytest.mark.asyncio
async def test_well_formed_open_orders_recording_passes_without_an_order_node():
    graph, fixture = open_orders_graph([{"order_id": "SIM-1"}])
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["observed"]["count"] == 1


@pytest.mark.asyncio
async def test_empty_open_orders_snapshot_passes_without_an_order_node():
    graph, fixture = open_orders_graph([])
    result = await replay(graph, fixture)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_open_orders_count_must_equal_row_total_without_an_order_node():
    graph, fixture = open_orders_graph([{"order_id": "SIM-1"}], count=2)
    result = await replay(graph, fixture)
    assert not result.passed
    assert any(e.get("path") == "open_orders" and e["code"] == "REPLAY_CONTRACT_FAILED"
               for e in result.errors), result.errors


@pytest.mark.asyncio
async def test_duplicate_open_order_ids_are_rejected_without_an_order_node():
    graph, fixture = open_orders_graph([{"order_id": "SIM-1"}, {"order_id": "SIM-1"}])
    result = await replay(graph, fixture)
    assert not result.passed
    assert any(e.get("path") == "open_orders" for e in result.errors), result.errors


def test_snapshot_contract_helper_rejects_missing_id_and_bad_count():
    with pytest.raises(ContractViolation) as excinfo:
        check_open_orders_snapshot({"open_orders": [{"symbol": "A"}], "count": 1})
    assert excinfo.value.code == "REPLAY_CONTRACT_FAILED"
    assert excinfo.value.path == "open_orders.open_orders[0].order_id"
    with pytest.raises(ContractViolation):
        check_open_orders_snapshot({"open_orders": [{"order_id": "X"}], "count": 5})
    assert check_open_orders_snapshot({"open_orders": [{"order_id": "X"}], "count": 1}) == {"X": {"order_id": "X"}}
    assert open_orders_snapshot_contract()["required"] == ["open_orders", "count"]


def test_order_events_shape_helper_rejects_incomplete_event():
    with pytest.raises(ContractViolation) as excinfo:
        check_order_events_shape([{"request_node": "cancel", "symbol_key": "NASDAQ:A", "applied": True}])
    assert excinfo.value.code == "REPLAY_CONTRACT_FAILED"
    assert excinfo.value.path.startswith("order_events")
    # A well-formed completion event passes the book-independent shape check.
    check_order_events_shape([{"request_node": "cancel", "symbol_key": "NASDAQ:A",
                              "event_id": "e1", "applied": True}])

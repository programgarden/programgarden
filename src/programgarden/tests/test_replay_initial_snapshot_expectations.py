"""The INITIAL fixture's expectations are judged on the initial run, not the final.

A subsequent `events` frame re-runs only the tick's downstream chain. When a
ThrottleNode (or any gate) blocks on that tick, the executor CLEARS the stale
downstream branch outputs (M-8). The final `outputs` snapshot therefore no longer
carries a node that produced a value on the initial run. Final acceptance must:

  * evaluate the INITIAL fixture's `expected`/`must_execute` against the outputs and
    executed list captured at the END OF THE MAIN FLOW (before the first frame), so a
    designer may legitimately assert the initial run's downstream output even though a
    later blocked tick clears it (regression: probe 9's `fill_recorder`);
  * still evaluate each FRAME's expectations against that frame's own post-frame
    snapshot, so a frame assertion on a node the frame cleared is reported as the
    frame's failure;
  * keep the simulated BOOK (`expected_simulation`) evaluated on the FINAL, cumulative
    simulation state — the ledger persists across frames even while node outputs clear.
"""
import pytest

from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.replay_external import recording
from programgarden.replay_scenarios import check_final_expectations
from programgarden.validation_replay import replay

AS_OF = "2026-09-22T14:00:00Z"
LATER = "2026-09-22T14:00:30Z"           # second tick, within the throttle interval
CONN = {"provider": "ls-sec.co.kr", "product": "overseas_stock"}
KEY = "NASDAQ:A"

# Reads the tick and echoes the close. It sits downstream of the throttle, so a
# blocked second tick clears its output.
RECORDER = (
    "def execute(data, params, context):\n"
    " bars = (params.get('bars') or {}).get('A') or []\n"
    " return {'close': bars[-1].get('close') if bars else None}\n")


def _feed(at, price):
    bars = {"A": [{"symbol": "A", "exchange": "NASDAQ", "date": "20260922",
                   "open": price, "high": price, "low": price, "close": price, "volume": 10}]}
    return recording("OverseasStockRealMarketDataNode",
                     {"symbol": {"symbol": "A", "exchange": "NASDAQ"}, "connection": CONN},
                     {"data": bars, "ohlcv_data": bars, "symbols": [{"symbol": "A", "exchange": "NASDAQ"}]},
                     {"type": "object", "required": ["data", "ohlcv_data", "symbols"]}, as_of=at)


def _broker_recording():
    return recording("OverseasStockBrokerNode", {}, {"connection": CONN},
                     {"type": "object", "required": ["connection"]}, as_of=AS_OF)


THROTTLED = {"type": "object", "required": ["_throttled"],
             "properties": {"_throttled": {"type": "boolean", "const": True}}}


def throttle_recorder_graph():
    """feed (recurring trigger) -> throttle -> recorder. On the second tick the
    throttle is in cooldown, so the recorder is cleared (M-8)."""
    nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        {"id": "feed", "type": "OverseasStockRealMarketDataNode", "symbol": {"symbol": "A", "exchange": "NASDAQ"}},
        {"id": "gate", "type": "ThrottleNode", "pass_first": True, "interval_sec": 300.0, "mode": "latest"},
        {"id": "recorder", "type": "CodeNode", "params": {"bars": "{{ nodes.feed.data }}"},
         "outputs": [{"name": "close", "type": "number"}], "code": RECORDER},
    ]
    edges = [{"from": "start", "to": "broker"}, {"from": "broker", "to": "feed"},
             {"from": "feed", "to": "gate"}, {"from": "gate", "to": "recorder"}]
    graph = {"id": "snap", "name": "Initial snapshot", "nodes": nodes, "edges": edges}
    fixture = {
        "as_of": AS_OF,
        "nodes": {"broker": _broker_recording(), "feed": _feed(AS_OF, 150)},
        # The INITIAL run asserts the downstream recorder value; the second tick clears it.
        "expected": {"recorder": {"type": "object", "const": {"close": 150}}},
        "must_execute": ["feed", "gate", "recorder"],
        "events": [{"as_of": LATER, "type": "market_data", "source_node_id": "feed",
                    "nodes": {"feed": _feed(LATER, 150)},
                    "must_execute": ["feed", "gate"],
                    "expected": {"gate": THROTTLED}}],
    }
    return graph, fixture


@pytest.mark.asyncio
async def test_initial_expected_on_a_node_the_second_tick_clears_still_passes():
    graph, fixture = throttle_recorder_graph()
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    # The blocked second tick cleared the recorder: the FINAL snapshot lost it...
    assert result.outputs.get("recorder") in (None, {})
    assert "recorder" not in result.events[0]["executed"]
    assert result.events[0]["outputs"]["gate"]["_throttled"] is True
    # ...but the INITIAL (main-flow) snapshot retained it, and that is what the initial
    # expected is judged against, so final acceptance PASSES.
    assert result.initial_outputs["recorder"] == {"close": 150}
    assert set(result.initial_executed) >= {"feed", "gate", "recorder"}
    check_final_expectations(result, fixture, graph)
    # Regression guard: judging the initial expected against the FINAL (cleared) output
    # — the pre-fix behaviour — would raise. The snapshot is what makes it pass.
    with pytest.raises(ContractViolation):
        check_contract(result.outputs.get("recorder"), fixture["expected"]["recorder"], "recorder")


@pytest.mark.asyncio
async def test_frame_expected_on_a_cleared_node_is_reported_as_a_frame_failure():
    graph, fixture = throttle_recorder_graph()
    # Assert the CLEARED node in the FRAME's own expected. The second tick blocked the
    # throttle and cleared `recorder`, so it has no post-frame output; final acceptance
    # checks every declared frame assertion (not only executed ones) and must FAIL here.
    fixture["events"][0]["expected"]["recorder"] = {"type": "object", "const": {"close": 150}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors            # replay itself has no error; the clear is a SKIP
    with pytest.raises(ContractViolation) as caught:
        check_final_expectations(result, fixture, graph)
    assert "recorder" in caught.value.path and caught.value.path.startswith("events.0")


def _sim_schema(cash, reserved, positions, orders):
    return {"type": "object",
            "required": ["cash", "reserved_cash", "positions", "orders", "live_order_count"],
            "properties": {
                "cash": {"type": "number", "const": cash},
                "reserved_cash": {"type": "number", "const": reserved},
                "positions": {"type": "object", "const": positions},
                "orders": orders,
                "live_order_count": {"type": "integer", "const": 0}}}


_FILLED_BOOK = {"type": "object", "required": ["SIM-order"], "properties": {
    "SIM-order": {"type": "object", "required": ["status", "filled_quantity"], "properties": {
        "status": {"type": "string", "const": "filled"},
        "filled_quantity": {"type": "integer", "const": 2}}}}}


def order_retrigger_graph():
    """feed (recurring trigger) -> throttle -> new-order. The main flow buys once; the
    second tick blocks the throttle so the order node is cleared, yet the simulated
    BOOK keeps the filled order — the ledger is cumulative, not cleared."""
    nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        {"id": "feed", "type": "OverseasStockRealMarketDataNode", "symbol": {"symbol": "A", "exchange": "NASDAQ"}},
        {"id": "gate", "type": "ThrottleNode", "pass_first": True, "interval_sec": 300.0, "mode": "latest"},
        {"id": "order", "type": "OverseasStockNewOrderNode", "side": "buy", "order_type": "limit",
         "order": {"symbol": "A", "exchange": "NASDAQ", "quantity": 2, "price": 100}},
    ]
    edges = [{"from": "start", "to": "broker"}, {"from": "broker", "to": "feed"},
             {"from": "feed", "to": "gate"}, {"from": "gate", "to": "order"}]
    graph = {"id": "book", "name": "Cumulative book", "nodes": nodes, "edges": edges}
    book = _sim_schema(800.0, 0, {KEY: 2}, _FILLED_BOOK)
    fixture = {
        "as_of": AS_OF,
        "nodes": {"broker": _broker_recording(), "feed": _feed(AS_OF, 100)},
        "broker": {"as_of": AS_OF, "account": {"cash": 1000, "currency": "USD", "max_investment": 600},
                   "instruments": {KEY: {"product": "overseas_stock", "currency": "USD", "price": 100,
                       "as_of": AS_OF, "session_open": True, "tradeable": True,
                       "tick_size": 0.01, "max_age_seconds": 60}}},
        "orders": {"order": {"response": "filled"}},
        # Initial expected on the order envelope (cleared by the second tick) plus the
        # cumulative book. The frame asserts only the throttle and the unchanged book.
        "expected": {"order": {"type": "object", "required": ["result"]}},
        "must_execute": ["feed", "gate", "order"],
        "expected_simulation": book,
        "events": [{"as_of": LATER, "type": "market_data", "source_node_id": "feed",
                    "nodes": {"feed": _feed(LATER, 100)},
                    "quotes": {KEY: {"price": 100, "as_of": LATER}},
                    "must_execute": ["feed", "gate"],
                    "expected": {"gate": THROTTLED},
                    "expected_simulation": book}],
    }
    return graph, fixture


@pytest.mark.asyncio
async def test_expected_simulation_stays_cumulative_while_node_outputs_clear():
    graph, fixture = order_retrigger_graph()
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    # The order node's OUTPUT was cleared by the blocked second tick...
    assert result.outputs.get("order") in (None, {})
    assert result.initial_outputs["order"]["result"][0]["filled_quantity"] == 2
    # ...yet the simulated BOOK persists cumulatively into the FINAL state.
    assert result.simulation["orders"]["SIM-order"]["status"] == "filled"
    assert result.simulation["cash"] == 800.0 and result.simulation["positions"] == {KEY: 2}
    assert result.simulation["live_order_count"] == 0
    # The frame's own post-frame book snapshot is the same single filled order.
    assert list(result.events[0]["simulation"]["orders"]) == ["SIM-order"]
    check_final_expectations(result, fixture, graph)


@pytest.mark.asyncio
async def test_final_book_is_the_cumulative_state_not_an_empty_ledger():
    # Control: asserting an EMPTY book fails — the filled order carries into the final
    # cumulative simulation and is not wiped by the clearing frame.
    graph, fixture = order_retrigger_graph()
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    empty = _sim_schema(1000.0, 0, {}, {"type": "object", "const": {}})
    fixture["expected_simulation"] = empty
    with pytest.raises(ContractViolation):
        check_final_expectations(result, fixture, graph)

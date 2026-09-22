"""Recorded ticks preserve state and run the real scheduler after initial build."""
from copy import deepcopy

import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_events import checked_events
from programgarden.replay_external import recording
from programgarden.replay_scenarios import check_final_expectations
from programgarden.validation_replay import replay
from tests.test_replay_sqlite import graph, sql
from tests.test_replay_order_adapter import case
from tests.test_validation_replay import code


AS_OF = "2026-09-22T14:00:00Z"


def counter():
    workflow = graph({"id": "schedule", "type": "ScheduleNode", "cron": "* * * * *", "timezone": "UTC"},
        sql("create", "CREATE TABLE IF NOT EXISTS observations (n INTEGER)"),
        sql("append", "INSERT INTO observations VALUES (1)"),
        sql("count", "SELECT COUNT(*) AS count FROM observations"))
    def expectation(count):
        return {"count": {"type": "object", "required": ["rows"], "properties": {
            "rows": {"type": "array", "const": [{"count": count}]}}}}
    fixture = {"as_of": AS_OF, "expected": expectation(3), "must_execute": ["count"], "events": [
        {"as_of": f"2026-09-22T14:0{minute}:00Z", "type": "schedule_tick", "source_node_id": "schedule",
         "expected": expectation(minute + 1), "must_execute": ["count"]} for minute in (1, 2)]}
    return workflow, fixture


@pytest.mark.asyncio
async def test_ticks_reuse_actual_sqlite_state_and_each_new_replay_starts_fresh():
    workflow, fixture = counter()
    for _ in range(2):
        result = await replay(workflow, fixture)
        assert result.passed, result.errors
        check_final_expectations(result, fixture, workflow)
        assert [e["outputs"]["count"]["rows"] for e in result.events] == [[{"count": 2}], [{"count": 3}]]
        assert result.executed.count("append") == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("change,reason", [
    (lambda w, f: f["events"][0].update(as_of="2026-09-22T14:00:30Z"), "cron instant"),
    (lambda w, f: w["nodes"][1].update(enabled=False), "disabled"),
    (lambda w, f: w["nodes"][1].update(count=1), "safety limits"),
    (lambda w, f: f["events"][0].update(type="order_event"), "schedule_tick"),
    (lambda w, f: f["events"][0].update(source_node_id="count"), "cannot emit"),
])
async def test_unrealizable_event_is_not_accepted(change, reason):
    workflow, fixture = counter()
    change(workflow, fixture)
    result = await replay(workflow, fixture)
    assert not result.passed
    assert any(reason in e.get("message", "") for e in result.errors), result.errors


@pytest.mark.asyncio
async def test_later_correct_state_does_not_hide_an_incorrect_intermediate_state():
    workflow, fixture = counter()
    result = await replay(workflow, fixture)
    assert result.passed
    fixture["events"][0]["expected"]["count"]["properties"]["rows"]["const"] = [{"count": 20}]
    with pytest.raises(ContractViolation):
        check_final_expectations(result, fixture, workflow)


@pytest.mark.asyncio
async def test_stock_repeat_is_not_silently_deduplicated_by_the_test_adapter():
    workflow, fixture = case()
    workflow["nodes"].insert(1, {"id": "schedule", "type": "ScheduleNode", "cron": "* * * * *", "timezone": "UTC"})
    workflow["edges"][0] = {"from": "start", "to": "schedule"}
    workflow["edges"].append({"from": "schedule", "to": "broker"})
    at = "2026-09-22T14:01:00Z"
    updated = deepcopy(fixture["nodes"])
    broker = updated["broker"]
    updated["broker"] = recording("OverseasStockBrokerNode",
        {"connection": broker["output"]["connection"]}, broker["output"], broker["contract"], as_of=at)
    fixture["events"] = [{"as_of": at, "type": "schedule_tick", "source_node_id": "schedule", "nodes": updated}]
    result = await replay(workflow, fixture)
    assert not result.passed
    assert len(result.simulation["orders"]) == 2, result.errors
    assert result.simulation["orders"]["SIM-2"]["reason"] == "position_already_held"
    assert result.simulation["positions"] == {"NASDAQ:A": 2}
    assert result.simulation["live_order_count"] == 0


@pytest.mark.parametrize("edit", [
    lambda f: f["events"][0].update(account={"cash": 99999}),
    lambda f: f["events"][0].update(trigger_nodes=["count"]),
    lambda f: f["events"][0].update(as_of="2026-09-22T13:59:00Z"),
    lambda f: f.update(events=f["events"] * 17),
])
def test_event_input_cannot_reset_state_or_choose_a_bypass_path(edit):
    _, fixture = counter()
    edit(fixture)
    with pytest.raises(ContractViolation):
        checked_events(fixture)


@pytest.mark.asyncio
async def test_final_verification_requires_each_declared_source_and_event_assertion():
    workflow, fixture = counter()
    result = await replay(workflow, fixture)
    fixture["events"][0].pop("expected")
    with pytest.raises(ContractViolation, match="independent"):
        check_final_expectations(result, fixture, workflow)
    workflow, fixture = counter()
    fixture["events"][0]["source_node_id"] = "absent"
    fixture["events"][1]["source_node_id"] = "absent"
    fixture["expected"]["count"]["properties"]["rows"]["const"] = [{"count": 1}]
    result = await replay(workflow, fixture)
    assert result.passed
    with pytest.raises(ContractViolation, match="Every declared"):
        check_final_expectations(result, fixture, workflow)


@pytest.mark.asyncio
async def test_real_market_events_honor_if_and_clear_the_previous_branch():
    feed = {"id": "feed", "type": "OverseasStockRealMarketDataNode",
            "symbol": {"symbol": "A", "exchange": "NASDAQ"}}
    workflow = graph({"id": "broker", "type": "OverseasStockBrokerNode"}, feed,
        code("last", "data['A'][0]['close']", data="{{ nodes.feed.data }}"),
        {"id": "guard", "type": "IfNode",
        "left": "{{ nodes.last.result }}", "operator": ">", "right": 100}, code("yes", "1"))
    workflow["edges"][-1]["from_port"] = "true"
    workflow["nodes"].append(code("no", "0"))
    workflow["edges"].append({"from": "guard", "to": "no", "from_port": "false"})
    connection = {"provider": "ls-sec.co.kr", "product": "overseas_stock"}
    def record(at, price):
        bars = {"A": [{"symbol": "A", "exchange": "NASDAQ", "date": "20260922",
            "open": 100, "high": max(100, price), "low": min(100, price), "close": price, "volume": 10}]}
        return recording(feed["type"], {"symbol": feed["symbol"], "connection": connection},
            {"data": bars, "ohlcv_data": bars, "symbols": [feed["symbol"]]},
            {"type": "object", "required": ["data", "ohlcv_data", "symbols"]}, as_of=at)
    at = "2026-09-22T14:00:01Z"
    fixture = {"as_of": AS_OF, "nodes": {"feed": record(AS_OF, 110),
        "broker": recording("OverseasStockBrokerNode", {}, {"connection": connection},
                            {"type": "object", "required": ["connection"]}, as_of=AS_OF)},
        "expected": {"no": {"type": "object", "const": {"result": 0}}},
        "must_execute": ["yes", "no"], "events": [{"as_of": at, "type": "market_data", "source_node_id": "feed",
            "nodes": {"feed": record(at, 90)}, "must_execute": ["feed", "last", "guard", "no"],
            "expected": {"no": {"type": "object", "const": {"result": 0}},
                         "yes": {"type": "object", "const": {}}}}]}
    result = await replay(workflow, fixture)
    assert result.passed, result.errors
    check_final_expectations(result, fixture, workflow)
    assert result.events[0]["executed"] == ["feed", "last", "guard", "no"]


@pytest.mark.asyncio
async def test_stock_repeat_after_a_long_gap_uses_the_new_clock_for_stale_quote_risk():
    workflow, fixture = case()
    workflow["nodes"].insert(1, {"id": "schedule", "type": "ScheduleNode", "cron": "*/2 * * * *", "timezone": "UTC"})
    workflow["edges"][0] = {"from": "start", "to": "schedule"}
    workflow["edges"].append({"from": "schedule", "to": "broker"})
    broker = fixture["nodes"]["broker"]
    at = "2026-09-22T14:02:00Z"
    fixture["events"] = [{"as_of": at, "type": "schedule_tick", "source_node_id": "schedule",
        "nodes": {"broker": recording("OverseasStockBrokerNode", {"connection": broker["output"]["connection"]},
                    broker["output"], broker["contract"], as_of=at)}}]
    result = await replay(workflow, fixture)
    assert not result.passed
    assert result.simulation["orders"]["SIM-2"]["reason"] == "stale_market_data"
    assert result.simulation["cash"] == 800

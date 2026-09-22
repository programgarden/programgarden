"""Actual scheduler/mappings reach simulated order intents without a transport."""
from copy import deepcopy
import pytest
from programgarden.validation_replay import replay
from programgarden.replay_external import recording

AS_OF="2026-09-22T14:00:00Z"


def case(product="OverseasStock",side="buy"):
    node={"id":"order","type":product+"NewOrderNode","side":side,"order_type":"limit",
          "order":{"symbol":"A","exchange":"NASDAQ","quantity":2,"price":100}}
    graph={"id":"orders","name":"Orders","nodes":[{"id":"start","type":"StartNode"},{"id":"broker","type":product+"BrokerNode"},node],
           "edges":[{"from":"start","to":"broker"},{"from":"broker","to":"order"}]}
    fixture={"nodes":{"broker":{"output":{"connection":{"product":"overseas_stock","provider":"ls-sec.co.kr"}},
            "contract":{"type":"object","required":["connection"],"properties":{"connection":{"type":"object"}}}}},"broker":{"as_of":AS_OF,"account":{"cash":1000,"currency":"USD","max_investment":600},
        "instruments":{"NASDAQ:A":{"product":"overseas_stock","currency":"USD","price":100,
            "as_of":AS_OF,"session_open":True,"tradeable":True,"tick_size":0.01,"max_age_seconds":60}}},
        "orders":{"order":{"response":"filled"}}}
    record = fixture["nodes"]["broker"]
    fixture["nodes"]["broker"] = recording(product+"BrokerNode", {}, record["output"], record["contract"], as_of=AS_OF)
    return graph,fixture


@pytest.mark.asyncio
async def test_graph_reaches_order_and_actual_result_envelope():
    graph,fixture=case()
    result=await replay(graph,fixture)
    assert result.passed,result.errors
    assert result.outputs["order"]["result"][0]["filled_quantity"]==2
    assert result.simulation["cash"]==800 and result.simulation["positions"]=={"NASDAQ:A":2}
    assert result.simulation["live_order_count"]==0 and not result.live_authorized


@pytest.mark.asyncio
async def test_wrong_quantity_blocks_before_any_intent_is_submitted():
    graph,fixture=case();graph["nodes"][2]["order"]["quantity"]="two"
    result=await replay(graph,fixture)
    assert not result.passed
    assert not result.simulation.get("orders")


@pytest.mark.asyncio
async def test_missing_response_scenario_is_not_invented_as_success():
    graph,fixture=case();fixture.pop("orders")
    result=await replay(graph,fixture)
    assert not result.passed and any(e["code"]=="REPLAY_FIXTURE_REQUIRED" for e in result.errors)


@pytest.mark.asyncio
async def test_rejection_is_preserved_in_observed_engine_state():
    graph,fixture=case();fixture["orders"]["order"]["response"]="rejected"
    result=await replay(graph,fixture)
    assert not result.passed
    assert result.simulation["cash"]==1000
    assert result.outputs["order"]["order_result"]["success"] is False
    assert result.node_states["order"]=="failed"


@pytest.mark.asyncio
async def test_timeout_remains_unknown_in_result_and_reserves_cash():
    graph,fixture=case();fixture["orders"]["order"]["response"]="timeout"
    result=await replay(graph,fixture)
    assert not result.passed
    assert result.outputs["order"]["order_result"]["status"]=="unknown"
    assert result.simulation["cash"]==1000 and not result.simulation["positions"]


@pytest.mark.asyncio
async def test_last_success_cannot_hide_an_earlier_iterated_rejection():
    graph,fixture=case()
    symbols=[{"symbol":"BAD","exchange":"NASDAQ"},
             {"symbol":"GOOD","exchange":"NASDAQ"}]
    graph["nodes"].insert(2,{"id":"watch","type":"WatchlistNode","symbols":symbols})
    # Watchlist intentionally emits symbol identities, not quantities. Use the
    # fixed explicit quantity and price while binding the current item identity.
    graph["nodes"][-1]["order"]={"symbol":"{{ item.symbol }}","exchange":"{{ item.exchange }}","quantity":2,"price":100}
    graph["edges"]=[{"from":"start","to":"broker"},{"from":"broker","to":"watch"},{"from":"watch","to":"order"}]
    instrument=fixture["broker"]["instruments"].pop("NASDAQ:A")
    fixture["broker"]["instruments"]={"NASDAQ:BAD":{**instrument,"tradeable":False},"NASDAQ:GOOD":instrument}
    result=await replay(graph,fixture)
    assert not result.passed
    assert [o["status"] for o in result.order_observations]==["rejected","filled"],result.errors
    assert result.simulation["positions"]=={"NASDAQ:GOOD":2}
    assert any(e["code"]=="REPLAY_ORDER_NOT_ACCEPTED" and e["reason"]=="instrument_not_tradeable" for e in result.errors)

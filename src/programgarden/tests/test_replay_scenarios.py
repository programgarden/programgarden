"""Expected risk failures remain failures in raw evidence; unrelated errors block."""
from copy import deepcopy
import pytest
from programgarden.incremental_build import BuildWorkspace
from programgarden.replay_scenarios import assess_scenario
from programgarden.validation_replay import replay
from tests.test_replay_order_adapter import case


def negative(response):
    graph,fixture=case()
    fixture["orders"]["order"]["response"]=response
    fixture["expected_order_failures"]=[{"node_id":"order","symbol_key":"NASDAQ:A",
        "status":"unknown" if response=="timeout" else "rejected",
        "reason":None if response=="timeout" else "simulated_broker_rejection","filled_quantity":0}]
    return graph,fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("response",["timeout","rejected"])
async def test_exact_negative_scenario_passes_without_rewriting_order_failure(response):
    graph,fixture=negative(response)
    result=await replay(graph,fixture)
    assert not result.passed and result.errors
    assert assess_scenario(result,fixture,graph)
    assert result.node_states["order"]=="failed"
    assert result.simulation["cash"]==1000 and result.simulation["positions"]=={}


@pytest.mark.asyncio
async def test_expected_rejection_does_not_waive_contract_or_mapping_errors():
    graph,fixture=negative("rejected")
    graph["nodes"][-1]["order"]["quantity"]="wrong"
    result=await replay(graph,fixture)
    assert not assess_scenario(result,fixture,graph)
    graph,fixture=negative("rejected")
    result=await replay(graph,fixture)
    result.errors.append({"code":"REPLAY_CONTRACT_FAILED","node_id":"order","message":"Wrong output type"})
    assert not assess_scenario(result,fixture,graph)


@pytest.mark.asyncio
async def test_unobserved_or_different_rejection_cannot_satisfy_fixture():
    graph,fixture=negative("rejected")
    fixture["orders"]["order"]["response"]="filled"
    result=await replay(graph,fixture)
    assert result.passed and not assess_scenario(result,fixture,graph)
    fixture["orders"]["order"]["response"]="timeout"
    result=await replay(graph,fixture)
    assert not assess_scenario(result,fixture,graph)


@pytest.mark.asyncio
async def test_positive_and_negative_suites_both_run_through_each_build_gate():
    graph,positive=case()
    _,rejected=negative("rejected")
    _,unknown=negative("timeout")
    for fixture in (positive,rejected,unknown):
        expected_success=fixture is positive
        fixture["expected"]={"order":{"type":"object","required":["order_result"],"properties":{
            "order_result":{"type":"object","required":["success"],"properties":{
                "success":{"type":"boolean","const":expected_success}}}}}}
        fixture["must_execute"]=["order"]
        fixture["expected_simulation"]={"type":"object",
            "required":["cash","reserved_cash","positions","orders","live_order_count"],"properties":{
                "cash":{"type":"number","const":800 if expected_success else 1000},
                "reserved_cash":{"type":"number","const":200 if fixture is unknown else 0},
                "positions":{"type":"object","const":{"NASDAQ:A":2} if expected_success else {}},
                "orders":{"type":"object","required":["SIM-order"],"properties":{
                    "SIM-order":{"type":"object","required":["status","filled_quantity"],"properties":{
                        "status":{"type":"string","const":"filled" if expected_success else "unknown" if fixture is unknown else "rejected"},
                        "filled_quantity":{"type":"integer","const":2 if expected_success else 0}}}}},
                "live_order_count":{"type":"integer","const":0}}}
    ws=BuildWorkspace("order-task",1,{**graph,"nodes":[],"edges":[]},[positive,rejected,unknown])
    for node in graph["nodes"]:
        ws.add_node(node,[e for e in graph["edges"] if e["to"]==node["id"]],expected_revision=ws.revision)
        proof=await ws.run_pending(node["id"],expected_revision=ws.revision)
        assert proof["passed"],proof["errors"]
    final=await ws.finalize(expected_revision=ws.revision)
    assert final["passed"] and ws.status=="READY"
    assert [r["passed"] for r in final["runs"]]==[True,False,False]
    assert all(r["scenario_passed"] for r in final["runs"])
    assert all(r["simulation"]["live_order_count"]==0 for r in final["runs"])

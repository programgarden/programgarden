"""Request acknowledgement is separate from matching completion evidence."""
import pytest

from programgarden.incremental_build import BuildWorkspace
from programgarden.replay_contracts import ContractViolation
from programgarden.replay_scenarios import assess_scenario
from programgarden.validation_replay import replay
from tests.test_replay_orders import book, intent
from tests.test_replay_order_adapter import case


def test_modify_reserves_original_until_confirmed_and_inherits_direction():
    b=book();first=b.submit(intent(quantity=2),key="original")
    request=b.request_change("modify",first["order_id"],key="modify",response="accepted",
                             replacement={"quantity":3,"price":110})
    assert b._reserved_cash()==330 and b.orders[first["order_id"]]["status"]=="accepted"
    assert b.cash==1000 and not b.positions
    b.confirm_change(request["request_id"],event_id="confirmed",applied=True)
    child=b.orders[request["replacement_order_id"]]
    assert child["intent"]["side"]=="buy" and child["intent"]["quantity"]==3
    assert b.orders[first["order_id"]]["status"]=="replaced" and b._reserved_cash()==330
    b.fill(child["order_id"],3,event_id="fill")
    assert b.cash==670 and b.positions=={"TEST:A":3}
    assert b._reserved_cash()==0


def test_partial_fill_cancel_ack_keeps_cash_and_remaining_reservation():
    b=book();first=b.submit(intent(),key="original",response="partial_fill",filled_quantity=2)
    request=b.request_change("cancel",first["order_id"],key="cancel",response="accepted")
    assert b._reserved_cash()==300 and b.cash==800 and b.positions=={"TEST:A":2}
    b.fill(first["order_id"],1,event_id="late-fill")
    assert b._reserved_cash()==200 and b.cash==700
    b.confirm_change(request["request_id"],event_id="cancelled",applied=True)
    assert b.cash==700 and b.positions=={"TEST:A":3} and b._reserved_cash()==0
    before=b.snapshot()
    b.confirm_change(request["request_id"],event_id="cancelled",applied=True)
    assert before==b.snapshot()
    with pytest.raises(ContractViolation):
        b.confirm_change(request["request_id"],event_id="cancelled",applied=False)


@pytest.mark.parametrize("action",["modify","cancel"])
def test_unknown_change_is_not_resent_and_explicit_evidence_reconciles(action):
    b=book();first=b.submit(intent(quantity=2),key="original")
    arguments={"replacement":{"quantity":3,"price":110}} if action=="modify" else {}
    request=b.request_change(action,first["order_id"],key="unknown",response="timeout",**arguments)
    again=b.request_change(action,first["order_id"],key="unknown",response="accepted",**arguments)
    assert again["status"]=="unknown" and again["duplicate"] and len(b.operations)==1
    reserve=330 if action=="modify" else 200
    assert b._reserved_cash()==reserve and b.cash==1000
    other=b.request_change("cancel",first["order_id"],key="different",response="accepted")
    assert other["status"]=="rejected" and other["reason"]=="operation_pending_or_unknown"
    b.confirm_change(request["request_id"],event_id="matched-evidence",applied=False)
    assert b._reserved_cash()==200 and b.orders[first["order_id"]]["status"]=="accepted"


@pytest.mark.parametrize("replacement,reason",[
    ({"quantity":7,"price":100},"max_investment_exceeded"),
    ({"quantity":3,"price":100.005},"invalid_price_tick"),
])
def test_rejected_modify_preserves_original_order(replacement,reason):
    b=book();first=b.submit(intent(quantity=2),key="original")
    request=b.request_change("modify",first["order_id"],key="modify",response="accepted",replacement=replacement)
    assert request["status"]=="rejected" and request["reason"]==reason
    assert b.orders[first["order_id"]]==first and b._reserved_cash()==200


def test_replacement_with_partial_fill_is_blocked_instead_of_guessing_quantity():
    b=book();first=b.submit(intent(),key="original",response="partial_fill",filled_quantity=2)
    with pytest.raises(ContractViolation,match="quantity semantics"):
        b.request_change("modify",first["order_id"],key="modify",response="accepted",
                         replacement={"quantity":3,"price":110})
    assert not b.operations and b._reserved_cash()==300


def test_late_fill_blocks_ambiguous_replace_confirmation_and_keeps_reservation():
    b=book();first=b.submit(intent(quantity=2),key="original")
    request=b.request_change("modify",first["order_id"],key="modify",response="accepted",
                             replacement={"quantity":3,"price":110})
    b.fill(first["order_id"],1,event_id="racing-fill")
    before=b.snapshot()
    with pytest.raises(ContractViolation,match="raced"):
        b.confirm_change(request["request_id"],event_id="replacement",applied=True)
    assert b.snapshot()==before and b._reserved_cash()==330


def test_changed_operation_key_is_rejected_without_replacing_original():
    b=book();first=b.submit(intent(quantity=2),key="original")
    b.request_change("modify",first["order_id"],key="modify",response="accepted",
                     replacement={"quantity":3,"price":110})
    before=b.snapshot()
    with pytest.raises(ContractViolation,match="cannot change"):
        b.request_change("modify",first["order_id"],key="modify",response="accepted",
                         replacement={"quantity":3,"price":120})
    assert b.snapshot()==before


def test_filled_original_does_not_erase_an_unknown_replacement():
    b=book(product="overseas_futures",margin_per_contract=200,multiplier=10)
    b.submit(intent(quantity=1),key="entry",response="filled")
    closing=b.submit(intent(side="sell",quantity=1),key="exit")
    b.request_change("modify",closing["order_id"],key="unknown",response="timeout",
                     replacement={"quantity":1,"price":110})
    b.fill(closing["order_id"],1,event_id="late-full-fill")
    assert b.positions=={"TEST:A":0}
    assert b.submit(intent(quantity=1),key="new-entry")["reason"]=="pending_or_unknown_order"


def lifecycle(product="OverseasStock",*,action="cancel",partial=False,confirm=True):
    graph,fixture=case(product)
    config=graph["nodes"][-1]["order"]
    if product=="KoreaStock":
        config.update(symbol="005930",exchange="KRX")
        instrument=fixture["broker"]["instruments"].pop("NASDAQ:A")
        instrument.update(product="korea_stock",currency="KRW",tick_size=1)
        fixture["broker"]["instruments"]={"KRX:005930":instrument}
        fixture["broker"]["account"]["currency"]="KRW"
    elif product=="OverseasFutures":
        config.update(symbol="MTEST",exchange="CME")
        instrument=fixture["broker"]["instruments"].pop("NASDAQ:A")
        instrument.update(product="overseas_futures",margin_per_contract=100,multiplier=10)
        fixture["broker"]["instruments"]={"CME:MTEST":instrument}
    scope=next(iter(fixture["broker"]["instruments"].values()))["product"]
    fixture["nodes"]["broker"]["output"]["connection"]["product"]=scope
    fixture["orders"]["order"]={"response":"partial_fill" if partial else "accepted", "filled_quantity":1 if partial else 0}
    node={"id":action,"type":product+action.title()+"OrderNode",
        "original_order_id":"{{ nodes.order.result[0].order_id }}", "symbol":config["symbol"],"exchange":config["exchange"]}
    if action=="modify": node["new_price"]=110
    graph["nodes"].append(node);graph["edges"].append({"from":"order","to":action})
    fixture["orders"][action]={"response":"accepted"}
    if confirm:
        graph["nodes"].append({"id":"observed","type":product+"OpenOrdersNode"})
        graph["edges"].append({"from":action,"to":"observed"})
        rows=[] if action=="cancel" else [{**config,"order_id":"SIM-REPLACE-1", "price":110,
            "side":"buy", "filled_quantity":0,"remaining_quantity":2}]
        fixture["nodes"]["observed"]={"output":{"open_orders":rows,"count":len(rows)},
            "contract":{"type":"object","required":["open_orders","count"]},
            "order_events":[{"request_node":action,"symbol_key":config["exchange"]+":"+config["symbol"],
                "event_id":"fixture-completion", "applied":True}]}
    return graph,fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("product",["KoreaStock","OverseasStock","OverseasFutures"])
@pytest.mark.parametrize("action",["modify","cancel"])
async def test_graph_change_and_following_observation_use_the_same_book(product,action):
    graph,fixture=lifecycle(product,action=action,partial=action=="cancel")
    result=await replay(graph,fixture)
    assert result.passed,result.errors
    request=result.outputs[action][action+"_result"]
    assert request["success"] and request["confirmation_pending"]
    assert result.simulation["operations"]["SIM-CHANGE-1"]["status"]=="confirmed"
    assert result.simulation["orders"]["SIM-1"]["status"]==("cancelled" if action=="cancel" else "replaced")
    assert result.simulation["live_order_count"]==0
    if action=="cancel":
        assert sum(result.simulation["positions"].values())==1


@pytest.mark.asyncio
async def test_cancel_ack_alone_does_not_remove_original_order():
    graph,fixture=lifecycle(confirm=False,partial=True)
    result=await replay(graph,fixture)
    assert result.passed,result.errors
    assert result.outputs["cancel"]["cancelled_order"]["status"]=="cancel_requested"
    assert result.simulation["orders"]["SIM-1"]["status"]=="partial_fill"


@pytest.mark.asyncio
async def test_empty_open_orders_cannot_invent_cancel_completion():
    graph,fixture=lifecycle(partial=True)
    fixture["nodes"]["observed"].pop("order_events")
    result=await replay(graph,fixture)
    assert not result.passed and any("contradicts" in e.get("message","") for e in result.errors)
    assert result.simulation["orders"]["SIM-1"]["status"]=="partial_fill"


@pytest.mark.asyncio
async def test_modify_keeps_futures_sell_direction_from_the_original():
    graph,fixture=lifecycle("OverseasFutures",action="modify")
    graph["nodes"][2]["side"]="sell"
    fixture["nodes"]["observed"]["output"]["open_orders"][0]["side"]="sell"
    result=await replay(graph,fixture)
    assert result.passed,result.errors
    assert result.simulation["orders"]["SIM-REPLACE-1"]["intent"]["side"]=="sell"


@pytest.mark.asyncio
async def test_stock_market_code_alias_matches_the_same_order():
    graph,fixture=lifecycle(action="modify")
    graph["nodes"][3]["exchange"]="82"
    fixture["nodes"]["observed"]["output"]["open_orders"][0]["exchange"]="82"
    result=await replay(graph,fixture)
    assert result.passed,result.errors


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value",[("symbol","OTHER"),("exchange","NYSE"),("original_order_id","SIM-UNKNOWN")])
async def test_change_cannot_target_a_different_order_identity(field,value):
    graph,fixture=lifecycle(confirm=False)
    graph["nodes"][3][field]=value
    result=await replay(graph,fixture)
    assert not result.passed and result.simulation["operations"]=={}


@pytest.mark.asyncio
async def test_wrong_exchange_in_observation_is_not_accepted_as_confirmation():
    graph,fixture=lifecycle(action="modify")
    fixture["nodes"]["observed"]["output"]["open_orders"][0]["exchange"]="NYSE"
    result=await replay(graph,fixture)
    assert not result.passed and any("exchange" in e.get("message","") for e in result.errors)


@pytest.mark.asyncio
@pytest.mark.parametrize("action",["modify","cancel"])
@pytest.mark.parametrize("response",["rejected","timeout"])
async def test_negative_change_scenarios_preserve_original_and_failure(action,response):
    graph,fixture=lifecycle(action=action,confirm=False)
    fixture["orders"][action]["response"]=response
    fixture["expected_order_failures"]=[{"node_id":action,"symbol_key":"NASDAQ:A",
        "status":"unknown" if response=="timeout" else "rejected",
        "reason":"order_outcome_unknown" if response=="timeout" else "simulated_broker_rejection", "filled_quantity":0}]
    result=await replay(graph,fixture)
    assert not result.passed and assess_scenario(result,fixture,graph),result.errors
    assert result.simulation["orders"]["SIM-1"]["status"]=="accepted"


@pytest.mark.asyncio
@pytest.mark.parametrize("expectation",["correct","absent","wrong_cash"])
async def test_incremental_cancel_final_replay_requires_actual_financial_state(expectation):
    graph,fixture=lifecycle(partial=True)
    fixture["expected"]={"observed":{"type":"object","required":["count"],
        "properties":{"count":{"type":"integer","const":0}}}}
    fixture["must_execute"]=["cancel","observed"]
    fixture["expected_simulation"]={"type":"object",
        "required":["cash","reserved_cash","positions","orders","live_order_count"],"properties":{
            "cash":{"type":"number","const":901 if expectation=="wrong_cash" else 900},
            "reserved_cash":{"type":"number","const":0},
            "positions":{"type":"object","const":{"NASDAQ:A":1}},
            "orders":{"type":"object","required":["SIM-1"],"properties":{
                "SIM-1":{"type":"object","required":["status","filled_quantity"],"properties":{
                    "status":{"type":"string","const":"cancelled"},"filled_quantity":{"type":"integer","const":1}}}}},
            "live_order_count":{"type":"integer","const":0}}}
    if expectation=="absent": fixture.pop("expected_simulation")
    workspace=BuildWorkspace("partial-cancel",1,{**graph,"nodes":[],"edges":[]},[fixture])
    for node in graph["nodes"]:
        workspace.add_node(node,[edge for edge in graph["edges"] if edge["to"]==node["id"]],expected_revision=workspace.revision)
        proof=await workspace.run_pending(node["id"],expected_revision=workspace.revision)
        assert proof["passed"],proof["errors"]
    final=await workspace.finalize(expected_revision=workspace.revision)
    assert final["passed"] is (expectation=="correct")
    assert workspace.status==("READY" if expectation=="correct" else "FAILED")
    assert final["runs"][0]["simulation"]["orders"]["SIM-1"]["status"]=="cancelled"

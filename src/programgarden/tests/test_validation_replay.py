"""Run actual CodeNode and If/filter semantics without a broker or model."""
import pytest
from programgarden.validation_replay import replay
from programgarden.replay_external import recording, request_identity

AS_OF = "2026-09-22T14:00:00Z"


def workflow(*nodes):
    nodes=[{"id":"start","type":"StartNode"},*nodes]
    return {"id":"replay-contract", "name":"Replay contract", "nodes":nodes,
        "edges":[{"from":a["id"],"to":b["id"]} for a,b in zip(nodes,nodes[1:])]}


def code(node_id="calc", value="1", kind="number", data=None):
    return {"id":node_id,"type":"CodeNode", "outputs":[{"name":"result","type":kind}],
        "code":f"def execute(data, params, context):\n return {{'result': {value}}}",
        **({"data":data} if data is not None else {})}


@pytest.mark.asyncio
async def test_actual_code_and_mapping_pass():
    result=await replay(workflow(code(), code("next", "data + 2", data="{{ nodes.calc.result }}")), {})
    assert result.passed, result.errors
    assert result.outputs["next"]["result"] == 3
    assert result.executed == ["start","calc","next"]
    assert not result.live_authorized


@pytest.mark.asyncio
async def test_type_failure_prevents_dependent_execution():
    result=await replay(workflow(code(value="'wrong'"), code("next")), {})
    assert not result.passed
    assert "next" not in result.executed
    assert any(e["code"] == "REPLAY_CONTRACT_FAILED" for e in result.errors)


@pytest.mark.asyncio
async def test_false_condition_is_not_forced_true():
    definition=workflow({"id":"gate","type":"IfNode","left":0,"operator":">","right":1},code("next"))
    definition["edges"][1]["from_port"]="true"
    result=await replay(definition,{})
    assert result.passed, result.errors
    assert "next" not in result.executed
    assert "next" in result.skipped


@pytest.mark.asyncio
async def test_input_contract_checked_before_executing_code():
    result=await replay(workflow(code(value="1 / 0", data={"price":1})), {
        "contracts":{"calc":{"input":{"type":"object","properties":{
            "data":{"type":"object","required":["close_price"]}}}}}})
    assert not result.passed
    assert "close_price" in result.errors[0]["path"]


@pytest.mark.asyncio
async def test_unsupported_external_node_is_blocked_instead_of_contacted():
    result=await replay(workflow({"id":"http","type":"HTTPRequestNode", "method":"POST", "url":"https://invalid.example/destructive"}),{})
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_REQUIRED" for e in result.errors)


@pytest.mark.asyncio
async def test_fixture_is_checked_and_never_merged_with_invented_defaults():
    definition=workflow({"id":"http","type":"HTTPRequestNode","method":"GET","url":"https://invalid.example/quote"})
    result=await replay(definition,{"as_of":AS_OF,"nodes":{"http":{"request":request_identity("HTTPRequestNode", {"method":"GET","url":"https://invalid.example/quote"}), "as_of":AS_OF,"item":None,"output":{"response":{"price":1}},
        "contract":{"type":"object","required":["response"],"properties":{
            "response":{"type":"object","required":["close_price"]}}}}}})
    assert not result.passed
    assert any("close_price" in e.get("path","") for e in result.errors)


@pytest.mark.asyncio
async def test_standalone_node_uses_exact_upstream_observation():
    definition=workflow(code(value="7"),code("next","data + 2",data="{{ nodes.calc.result }}"))
    result=await replay(definition,{},node_under_test="next")
    assert result.passed, result.errors
    assert result.executed == ["next"]
    assert result.setup_executed == ["start", "calc"]
    assert result.outputs["next"]["result"] == 9


@pytest.mark.asyncio
async def test_expression_and_code_worker_share_the_same_fixture_clock():
    definition=workflow(code(value="context.date.today() + ':' + data",kind="string",data="{{ date.ago(1) }}"))
    result=await replay(definition,{"as_of":"2026-01-01T00:15:00+09:00"})
    assert result.passed,result.errors
    assert result.outputs["calc"]["result"]=="2026-01-01:2025-12-31"


@pytest.mark.asyncio
async def test_multi_symbol_io_uses_exact_item_without_squared_duplication():
    symbols=[{"symbol":"XOM","exchange":"NYSE"},{"symbol":"CVX","exchange":"NYSE"}]
    definition=workflow({"id":"broker","type":"OverseasStockBrokerNode"},
        {"id":"watch","type":"WatchlistNode","symbols":symbols},
        {"id":"quotes","type":"OverseasStockMarketDataNode","symbols":"{{ nodes.watch.symbols }}"},
        code("count","len(data)",data="{{ nodes.quotes.values }}"))
    fixture={"as_of":AS_OF,"nodes":{"broker":{"output":{"connection":{"product":"overseas_stock"}},
        "contract":{"type":"object","required":["connection"]}},"quotes":{"items":{}}}}
    for index,symbol in enumerate(symbols):
        value={**symbol,"price":100+index}
        fixture["nodes"]["quotes"]["items"]["NYSE:"+symbol["symbol"]]={
            "output":{"value":value,"values":[value]},
            "contract":{"type":"object","required":["value","values"]}}
    broker = fixture["nodes"]["broker"]
    fixture["nodes"]["broker"] = recording("OverseasStockBrokerNode", {}, broker["output"], broker["contract"], as_of=AS_OF)
    for symbol in symbols:
        row = fixture["nodes"]["quotes"]["items"]["NYSE:"+symbol["symbol"]]
        fixture["nodes"]["quotes"]["items"]["NYSE:"+symbol["symbol"]] = recording("OverseasStockMarketDataNode", {"symbols":symbols}, row["output"], row["contract"], as_of=AS_OF, item=symbol)
    result=await replay(definition,fixture)
    assert result.passed,result.errors
    assert result.outputs["count"]["result"]==2
    assert [row["symbol"] for row in result.outputs["quotes"]["values"]]==["XOM","CVX"]

"""A schema-valid external output cannot certify a different resolved request."""
from copy import deepcopy

import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_external import recording, request_identity
from programgarden.validation_replay import replay
from tests.test_validation_replay import workflow, code

AS_OF = "2026-09-22T14:00:00Z"
HTTP = {"method": "GET", "url": "https://fixture.invalid/prices", "query_params": {"currency": "USD"}}
CONTRACT = {"type": "object", "required": ["response"], "properties": {"response": {
    "type": "object", "required": ["price"], "properties": {"price": {"type": "number"}}}}}


def http_case():
    graph = workflow({"id": "source", "type": "HTTPRequestNode", **HTTP},
                     code(data="{{ nodes.source.response.price }}", value="data + 1"))
    fixture = {"as_of": AS_OF, "nodes": {"source": recording(
        "HTTPRequestNode", HTTP, {"response": {"price": 10}}, CONTRACT, as_of=AS_OF)}}
    return graph, fixture


@pytest.mark.asyncio
async def test_matching_request_runs_actual_downstream_computation():
    graph, fixture = http_case()
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["calc"]["result"] == 11
    assert not result.live_authorized


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"url": "https://fixture.invalid/wrong"}, {"method": "POST"},
    {"query_params": {"currency": "KRW"}}, {"body": {"side": "buy"}},
])
async def test_changed_request_blocks_before_dependent_code(change):
    graph, fixture = http_case()
    graph["nodes"][1].update(change)
    result = await replay(graph, fixture)
    assert not result.passed
    assert "calc" not in result.executed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors), result.errors


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["clock", "item", "missing_request", "missing_clock"])
async def test_recording_cannot_cross_clock_or_iteration(change):
    graph, fixture = http_case()
    record = fixture["nodes"]["source"]
    if change == "clock": record["as_of"] = "2026-09-23T14:00:00Z"
    elif change == "item": record["item"] = {"symbol": "WRONG"}
    elif change == "missing_request": record.pop("request")
    else: fixture.pop("as_of")
    result = await replay(graph, fixture)
    assert not result.passed and "calc" not in result.executed
    assert any(e["code"] in {"REPLAY_FIXTURE_MISMATCH", "REPLAY_FIXTURE_REQUIRED"} for e in result.errors)


def test_default_normalization_does_not_hide_executable_fields():
    a = request_identity("OverseasStockBrokerNode", {})
    assert a == request_identity("OverseasStockBrokerNode", {"paper_trading": False, "name": "Renamed"})
    assert a != request_identity("OverseasStockBrokerNode", {"paper_trading": True})
    assert a != request_identity("KoreaStockBrokerNode", {})
    with pytest.raises(ContractViolation, match="Unknown recording request fields"):
        request_identity("OverseasStockBrokerNode", {"unrecognized_filter": True})


@pytest.mark.parametrize("changed", [
    {"symbols": [{"symbol": "CVX", "exchange": "NYSE"}]},
    {"start_date": "20260902"}, {"end_date": "20260923"}, {"interval": "1m"},
])
def test_history_request_identity_preserves_symbol_dates_and_interval(changed):
    request = {"symbols": [{"symbol": "XOM", "exchange": "NYSE"}],
               "start_date": "20260901", "end_date": "20260922", "interval": "1d"}
    assert request_identity("OverseasStockHistoricalDataNode", request) != request_identity(
        "OverseasStockHistoricalDataNode", {**request, **changed})


def test_recording_copies_inputs_and_checks_output_contract():
    graph, fixture = http_case()
    original = deepcopy(fixture)
    graph["nodes"][1]["query_params"]["currency"] = "EUR"
    assert fixture == original
    with pytest.raises(ContractViolation):
        recording("HTTPRequestNode", HTTP, {"response": {}}, CONTRACT, as_of=AS_OF)

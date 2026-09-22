"""Exercise provider normalization and market identity without any API access."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from programgarden.validation_replay import replay
from programgarden_community.nodes.market.fmp import FundamentalDataNode


def case():
    graph = {"id": "fundamental-replay", "name": "Fundamental replay", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "fmp", "type": "FundamentalDataNode", "data_type": "profile",
         "symbols": [{"symbol": "XOM", "exchange": "NYSE"}, {"symbol": "CVX", "exchange": "NYSE"}]},
        {"id": "filter", "type": "CodeNode", "data": "{{ nodes.fmp.data }}",
         "outputs": [{"name": "symbols", "type": "array"}],
         "code": "def execute(data, params, context):\n return {'symbols': [r['symbol'] for r in data if 0 < r['per'] <= 20]}"},
    ], "edges": [{"from": "start", "to": "fmp"}, {"from": "fmp", "to": "filter"}]}
    fixture = {"nodes": {"fmp": {"requests": [{
        "request": {"path": "/api/v3/profile/XOM,CVX", "query": {}},
        "response": [{"symbol": "XOM", "exchangeShortName": "NYSE", "pe": 15.5},
                     {"symbol": "CVX", "exchangeShortName": "NYSE", "pe": 25.0}],
        "contract": {"type": "array", "items": {"type": "object",
            "required": ["symbol", "exchangeShortName", "pe"],
            "properties": {"pe": {"type": ["number", "null"]}}}},
    }]}}}
    return graph, fixture


@pytest.mark.asyncio
async def test_actual_fmp_normalization_and_downstream_filter_without_transport():
    graph, fixture = case()
    with patch.object(FundamentalDataNode, "_fetch_api", side_effect=AssertionError("Live transport forbidden")):
        result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["fmp"]["data"][0]["per"] == 15.5
    assert result.outputs["filter"]["symbols"] == ["XOM"]
    assert result.outputs["fmp"]["summary"]["record_count"] == 2
    assert not result.live_authorized


@pytest.mark.asyncio
async def test_missing_pe_uses_actual_normalizer_and_does_not_invent_an_entry():
    graph, fixture = case()
    fixture["nodes"]["fmp"]["requests"][0]["response"][0]["pe"] = None
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["filter"]["symbols"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["missing", "path", "query", "response", "extra", "unsupported"])
async def test_unmatched_or_invalid_fmp_evidence_cannot_pass(mutation):
    graph, fixture = case()
    recording = fixture["nodes"]["fmp"]["requests"][0]
    if mutation == "missing":
        fixture = {}
    elif mutation == "path":
        recording["request"]["path"] = "/api/v3/profile/DIFFERENT"
    elif mutation == "query":
        recording["request"]["query"] = {"limit": "10"}
    elif mutation == "response":
        recording["response"][0]["pe"] = "not a number"
    elif mutation == "extra":
        fixture["nodes"]["fmp"]["requests"].append(deepcopy(recording))
    else:
        graph["nodes"][1]["data_type"] = "ratios"
    with patch.object(FundamentalDataNode, "_fetch_api", side_effect=AssertionError("Live transport forbidden")):
        result = await replay(graph, fixture)
    assert not result.passed
    assert "filter" not in result.executed


@pytest.mark.asyncio
async def test_domestic_iteration_does_not_require_an_overseas_exchange_field():
    graph = {"id": "domestic-replay", "name": "Domestic replay", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "KoreaStockBrokerNode"},
        {"id": "watch", "type": "WatchlistNode", "symbols": [{"symbol": "005930"}, {"symbol": "000660"}]},
        {"id": "quotes", "type": "KoreaStockMarketDataNode", "symbols": "{{ nodes.watch.symbols }}"},
    ], "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "watch"},
                 {"from": "watch", "to": "quotes"}]}
    fixture = {"nodes": {"broker": {"output": {"connection": {"product": "korea_stock"}},
        "contract": {"type": "object", "required": ["connection"]}}, "quotes": {"items": {}}}}
    for symbol in ("005930", "000660"):
        value = {"symbol": symbol, "exchange": "KRX", "price": 70000}
        fixture["nodes"]["quotes"]["items"]["KRX:" + symbol] = {
            "output": {"value": value, "values": [value]},
            "contract": {"type": "object", "required": ["value", "values"]}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert [r["symbol"] for r in result.outputs["quotes"]["values"]] == ["005930", "000660"]


@pytest.mark.asyncio
@pytest.mark.parametrize("whole_array", [False, True])
async def test_fmp_iteration_checks_actual_request_instead_of_narrowing_to_fixture(whole_array):
    graph, fixture = case()
    symbols = deepcopy(graph["nodes"][1]["symbols"])
    graph["nodes"].insert(1, {"id": "watch", "type": "WatchlistNode", "symbols": symbols})
    graph["nodes"][2]["symbols"] = ("{{ nodes.watch.symbols }}" if whole_array else
        [{"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}"}])
    graph["edges"] = [{"from": "start", "to": "watch"}, {"from": "watch", "to": "fmp"},
                      {"from": "fmp", "to": "filter"}]
    batch = fixture["nodes"]["fmp"]["requests"][0]
    fixture["nodes"]["fmp"] = {"items": {}}
    for row in batch["response"]:
        recording = deepcopy(batch)
        recording["request"]["path"] = "/api/v3/profile/" + row["symbol"]
        recording["response"] = [row]
        fixture["nodes"]["fmp"]["items"]["NYSE:" + row["symbol"]] = {"requests": [recording]}
    with patch.object(FundamentalDataNode, "_fetch_api", side_effect=AssertionError("Live transport forbidden")):
        result = await replay(graph, fixture)
    if whole_array:
        assert not result.passed
        assert "filter" not in result.executed
    else:
        assert result.passed, result.errors
        assert [row["symbol"] for row in result.outputs["fmp"]["data"]] == ["XOM", "CVX"]


@pytest.mark.asyncio
async def test_key_metrics_recording_keeps_period_limit_and_real_field_mapping():
    graph, fixture = case()
    graph["nodes"] = graph["nodes"][:2]
    graph["edges"] = graph["edges"][:1]
    graph["nodes"][1].update(data_type="key_metrics", period="quarter", limit=2,
                             symbols=[{"symbol": "XOM", "exchange": "NYSE"}])
    fixture["nodes"]["fmp"]["requests"] = [{
        "request": {"path": "/api/v3/key-metrics/XOM", "query": {"period": "quarter", "limit": "2"}},
        "response": [{"date": "2026-06-30", "roe": 0.15, "roic": 0.12}],
        "contract": {"type": "array", "items": {"type": "object", "required": ["date", "roe", "roic"]}},
    }]
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    row = result.outputs["fmp"]["data"][0]
    assert (row["symbol"], row["exchange"], row["roe"], row["roic"]) == ("XOM", "NYSE", 0.15, 0.12)

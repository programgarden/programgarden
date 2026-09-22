"""Recorded I/O is parsed and filtered by native code, never supplied as a pass."""
import base64
from copy import deepcopy
from unittest.mock import patch

import pytest

from programgarden.replay_external import source_recording, recording
from programgarden.validation_replay import replay
from tests.test_validation_replay import workflow

AS_OF = "2026-09-22T14:00:00Z"


def test_every_registered_node_has_an_explicit_replay_boundary():
    from programgarden.executor import WorkflowExecutor
    from programgarden_core import NodeTypeRegistry
    from programgarden.validation_replay import COMPUTATION_NODES, FIXTURE_NODES, SOURCE_NODES, ORDER_NODES
    WorkflowExecutor()
    covered = COMPUTATION_NODES | FIXTURE_NODES | SOURCE_NODES | ORDER_NODES | {
        "SQLiteNode", "SessionGateNode", "ScheduleNode", "TradingHoursFilterNode"}
    assert set(NodeTypeRegistry().list_types()) == covered


def fixture(node, source):
    return {"as_of": AS_OF, "nodes": {node["id"]: source_recording(node["type"], node, source,
        {"type": "object"}, as_of=AS_OF)}}


def futures_case(node, source):
    broker = {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fixture-broker",
              "paper_trading": True}
    graph = workflow(broker, node)
    graph["credentials"] = [{"credential_id": "fixture-broker", "type": "broker_ls_overseas_futures"}]
    data = fixture(node, source)
    data["nodes"]["broker"] = recording(broker["type"], broker, {"connection": {
        "provider": "ls-sec.co.kr", "product": "overseas_futures", "credential_id": "fixture-broker",
        "paper_trading": True}}, {"type": "object"}, as_of=AS_OF)
    data["nodes"][node["id"]]["request"]["connection"] = deepcopy(data["nodes"]["broker"]["output"]["connection"])
    return graph, data


@pytest.mark.asyncio
@pytest.mark.parametrize("score,label", [(12.25, "Extreme Fear"), (67.25, "Greed")])
async def test_sentiment_parses_raw_provider_values(score, label):
    node = {"id": "sentiment", "type": "FearGreedIndexNode"}
    source = {"fear_and_greed": {"score": score, "previous_close": 51.0}}
    result = await replay(workflow(node), fixture(node, source))
    assert result.passed, result.errors
    assert result.outputs["sentiment"] == {"value": round(score, 1), "label": label, "previous_close": 51.0}


@pytest.mark.asyncio
async def test_missing_sentiment_score_is_not_fabricated_as_zero():
    node = {"id": "sentiment", "type": "FearGreedIndexNode"}
    result = await replay(workflow(node), fixture(node, {"fear_and_greed": {}}))
    assert not result.passed


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt,content,expected", [
    ("csv", 'symbol,price\nA,12\n', [{"symbol": "A", "price": "12"}]),
    ("json", '{"symbol":"A","price":12}', {"symbol": "A", "price": 12}),
])
async def test_native_file_parser_uses_recorded_bytes_not_host_files(fmt, content, expected):
    from programgarden_community.nodes.data.file_reader import FileReaderNode
    path = "inputs/prices." + fmt
    node = {"id": "file", "type": "FileReaderNode", "file_path": path, "format": fmt}
    source = {"files": {path: base64.b64encode(content.encode()).decode()}}
    with patch.object(FileReaderNode, "_validate_path", side_effect=AssertionError("Host read forbidden")):
        result = await replay(workflow(node), fixture(node, source))
    assert result.passed, result.errors
    assert result.outputs["file"]["data_list"] == [expected]
    assert result.outputs["file"]["metadata"][0]["file_name"] == "prices." + fmt


@pytest.mark.asyncio
async def test_missing_file_and_changed_path_fail():
    node = {"id": "file", "type": "FileReaderNode", "file_path": "a.json", "format": "json"}
    data = fixture(node, {"files": {}})
    assert not (await replay(workflow(node), data)).passed
    node["file_path"] = "b.json"
    assert not (await replay(workflow(node), data)).passed


@pytest.mark.asyncio
async def test_universe_normalizes_actual_listing_exchange():
    node = {"id": "universe", "type": "MarketUniverseNode", "universe": "SP500"}
    data = fixture(node, {"index": "S&P 500", "stocks": [{"symbol": "A", "name": "Fixture A",
        "symbols": [{"google": "FRA:A", "currency": "EUR"}, {"google": "NYSE:A", "currency": "USD"}]}]})
    result = await replay(workflow(node), data)
    assert result.passed, result.errors
    assert result.outputs["universe"]["symbols"] == [{"symbol": "A", "exchange": "NYSE", "name": "Fixture A"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("choice,symbol", [("front", "HMHU26"), ("next", "HMHZ26")])
async def test_native_contract_selection_discards_expired_rows(choice, symbol):
    node = {"id": "contract", "type": "FuturesContractNode", "base_products": ["HMH"], "contract_selection": choice}
    rows = [{"Symbol": f"HMH{month}26", "BscGdsCd": "HMH", "ExchCd": "HKEX",
        "LstngYr": "2026", "LstngM": month} for month in ["N", "U", "Z"]]
    result = await replay(*futures_case(node, {"rows": rows}))
    assert result.passed, result.errors
    assert result.outputs["contract"]["symbols"] == [{"symbol": symbol, "exchange": "HKEX"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [False, True])
async def test_screener_applies_actual_thresholds_and_requires_every_lookup(missing):
    node = {"id": "screen", "type": "ScreenerNode", "data_source": "yfinance", "price_min": 10.0,
        "symbols": [{"symbol": "A", "exchange": "NYSE"}, {"symbol": "B", "exchange": "NYSE"}]}
    quotes = {"A": {"regularMarketPrice": 11.0, "marketCap": 1000, "exchange": "NYQ"}}
    if not missing:
        quotes["B"] = {"regularMarketPrice": 9.0, "marketCap": 1000, "exchange": "NYQ"}
    result = await replay(workflow(node), fixture(node, {"quotes": quotes}))
    assert result.passed is not missing, result.errors
    if not missing:
        assert [s["symbol"] for s in result.outputs["screen"]["symbols"]] == ["A"]


@pytest.mark.asyncio
@pytest.mark.parametrize("quantity", [0, 2])
async def test_order_capacity_checks_native_response_echo(quantity):
    from tests.test_futures_orderable_evidence import config, response
    node = {"id": "capacity", "type": "OverseasFuturesOrderableQuantityNode", **config()}
    node.pop("connection")
    source = response(quantity).model_dump(mode="json", exclude_unset=True)
    result = await replay(*futures_case(node, source))
    assert result.passed, result.errors
    assert result.outputs["capacity"]["quantity"] == quantity
    broken = deepcopy(source)
    broken["block1"]["IsuCodeVal"] = "ANOTHER"
    assert not (await replay(*futures_case(node, broken))).passed


def stock_screener(node, source):
    broker = {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "fixture-stock"}
    graph = workflow(broker, node)
    graph["credentials"] = [{"credential_id": "fixture-stock", "type": "broker_ls_overseas_stock"}]
    connection = {"provider": "ls-sec.co.kr", "product": "overseas_stock", "credential_id": "fixture-stock",
                  "paper_trading": False, "broker_node_id": "broker"}
    data = fixture({**node, "connection": connection}, source)
    data["nodes"]["broker"] = recording(broker["type"], broker, {"connection": connection},
        {"type": "object"}, as_of=AS_OF)
    return graph, data


def raw_quote(symbol, price, volume=1000, exchange="81"):
    return {"keysymbol": exchange + symbol, "symbol": symbol, "exchcd": exchange,
            "price": str(price), "volume": volume}


@pytest.mark.asyncio
@pytest.mark.parametrize("minimum,expected", [(10.0, ["A"]), (50.0, [])])
async def test_ls_screener_uses_native_quote_parser_and_zero_matches_is_valid(minimum, expected):
    node = {"id": "screen", "type": "ScreenerNode", "data_source": "ls", "price_min": minimum,
            "volume_min": 500, "symbols": [{"symbol": "A", "exchange": "NYSE"},
                                         {"symbol": "B", "exchange": "NYSE"}]}
    source = {"g3101": {"81A": raw_quote("A", 11), "81B": raw_quote("B", 9)}}
    with patch("programgarden.executor.ensure_ls_login", side_effect=AssertionError("Login forbidden")):
        result = await replay(*stock_screener(node, source))
    assert result.passed, result.errors
    assert [row["symbol"] for row in result.outputs["screen"]["symbols"]] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["missing_quote", "missing_price", "wrong_symbol", "wrong_exchange",
                                   "wrong_key", "zero_price", "negative_volume", "sector", "market_cap"])
async def test_ls_screener_never_ignores_unavailable_filter_evidence(change):
    node = {"id": "screen", "type": "ScreenerNode", "data_source": "ls", "price_min": 10.0,
            "symbols": [{"symbol": "A", "exchange": "NYSE"}]}
    quote = raw_quote("A", 11)
    if change == "missing_price": quote.pop("price")
    if change == "wrong_symbol": quote["symbol"] = "OTHER"
    if change == "wrong_exchange": quote["exchcd"] = "82"
    if change == "wrong_key": quote["keysymbol"] = "82A"
    if change == "zero_price": quote["price"] = "0"
    if change == "negative_volume": quote["volume"] = -1
    if change == "sector": node["sector"] = "Energy"
    if change == "market_cap": node["market_cap_min"] = 1000.0
    source = {"g3101": {} if change == "missing_quote" else {"81A": quote}}
    result = await replay(*stock_screener(node, source))
    assert not result.passed


def test_ls_quote_request_and_consumed_fields_match_sdk_contract():
    from programgarden.executor import ScreenerNodeExecutor
    from programgarden_finance.ls.overseas_stock.market.g3101.blocks import G3101OutBlock, G3101Response
    assert {"symbol", "keysymbol", "exchcd", "price", "volume"} <= G3101OutBlock.model_fields.keys()
    assert {"block", "rsp_cd", "error_msg", "status_code"} <= G3101Response.model_fields.keys()
    for name, code in [("NYSE", "81"), ("AMEX", "81"), ("NASDAQ", "82")]:
        request = ScreenerNodeExecutor.stock_quote_request({"symbol": "A", "exchange": name})
        assert request.model_dump() == {"delaygb": "R", "keysymbol": code + "A", "exchcd": code, "symbol": "A"}
    with pytest.raises(ValueError):
        ScreenerNodeExecutor.stock_quote_request({"symbol": "A", "exchange": "UNKNOWN"})


@pytest.mark.asyncio
async def test_ls_screener_preserves_numeric_master_fields_and_filters_volume():
    node = {"id": "screen", "type": "ScreenerNode", "data_source": "ls", "price_min": 10.0,
            "market_cap_min": 100.0, "volume_min": 500,
            "symbols": [{"symbol": "A", "exchange": "NYSE", "price": 11.0, "market_cap": 1000},
                        {"symbol": "B", "exchange": "NYSE", "price": 12.0, "market_cap": 2000}]}
    source = {"g3101": {"81A": raw_quote("A", 11, 1000), "81B": raw_quote("B", 12, 100)}}
    result = await replay(*stock_screener(node, source))
    assert result.passed, result.errors
    assert [(r["symbol"], r["market_cap"], r["volume"]) for r in result.outputs["screen"]["symbols"]] == [("A", 1000, 1000)]


@pytest.mark.asyncio
async def test_ls_screener_mixed_master_watchlist_does_not_drop_unenriched_input():
    node = {"id": "screen", "type": "ScreenerNode", "data_source": "ls", "price_min": 10.0,
            "symbols": [{"symbol": "A", "exchange": "NYSE", "price": 11.0, "market_cap": 1000},
                        {"symbol": "B", "exchange": "NYSE"}]}
    result = await replay(*stock_screener(node, {"g3101": {"81B": raw_quote("B", 12)}}))
    assert result.passed, result.errors
    assert [r["symbol"] for r in result.outputs["screen"]["symbols"]] == ["A", "B"]

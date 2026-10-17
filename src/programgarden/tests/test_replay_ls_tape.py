"""ls_tape: LS REST read nodes run their REAL executors over recorded HTTP answers.

The tapes are synthetic (``fixtures/ls_tape_synthetic_20261018.json``): finance
block models filled from a scenario ledger. ``expected`` is the read method's own
output over the same tape, so these tests check that the full replay path (connection
injection, placeholder credential, replay LS client, finance transport, parser) gives
exactly what the live node code gives, with every socket blocked.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from programgarden.replay_external import recording
from programgarden.validation_replay import replay

AS_OF = "2026-10-16T14:00:00Z"
SCENARIOS = json.loads((Path(__file__).parent / "fixtures" / "ls_tape_synthetic_20261018.json")
                       .read_text())["scenarios"]
BROKERS = {"overseas_stock": "OverseasStockBrokerNode", "korea_stock": "KoreaStockBrokerNode",
           "overseas_futures": "OverseasFuturesBrokerNode"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("network access during an ls_tape replay")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    from programgarden.executor import LSClientManager
    before = dict(LSClientManager._instances)
    yield
    assert LSClientManager._instances == before  # a replay client is never cached


def _stable(value):
    """Drop ``observed_at``: live read code stamps the worker's wall clock there."""
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k != "observed_at"}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def _case(scenario, node_type, config=None, *, paper=None):
    data = SCENARIOS[scenario]
    product = data["ledger"]["product"]
    paper = data["ledger"]["paper"] if paper is None else paper
    connection = {"product": product, "provider": "ls-sec.co.kr", "paper_trading": paper}
    graph = {"id": "tape", "name": "Tape", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": BROKERS[product], **({"paper_trading": True} if paper else {})},
        {"id": "read", "type": node_type, **(config or {})}],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "read"}]}
    broker_config = {"paper_trading": True} if paper else {}
    fixture = {"as_of": AS_OF, "nodes": {
        "broker": recording(BROKERS[product], broker_config, {"connection": connection},
                            {"type": "object", "required": ["connection"]}, as_of=AS_OF),
        "read": {"kind": "ls_tape", "as_of": AS_OF, "tape": deepcopy(data["tape"])}}}
    return graph, fixture, data["expected"]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,node_type", [
    ("overseas_stock_account_holding", "OverseasStockAccountNode"),
    ("overseas_stock_account_cash_only", "OverseasStockAccountNode"),
    ("korea_stock_account_holding", "KoreaStockAccountNode"),
    ("korea_stock_open_orders_empty", "KoreaStockOpenOrdersNode"),
    ("korea_stock_open_orders_pending", "KoreaStockOpenOrdersNode"),
    ("overseas_stock_open_orders_empty", "OverseasStockOpenOrdersNode"),
    ("overseas_futures_account_paper_empty", "OverseasFuturesAccountNode"),
    ("overseas_futures_account_holding", "OverseasFuturesAccountNode"),
])
async def test_account_and_open_orders_nodes_run_their_live_code(scenario, node_type):
    graph, fixture, expected = _case(scenario, node_type)
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert _stable(result.outputs["read"]) == _stable(expected)
    assert result.assumptions[-1]["kind"] == "ls_tape" and result.assumptions[-1]["node_id"] == "read"


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,interval,dates", [
    ("overseas_stock_daily_bars", "1d", ("20260801", "20261016")),
    ("overseas_stock_minute_bars_15m", "15m", ("20261015", "20261016")),
])
async def test_history_node_runs_g3204_and_g3203_from_the_tape(scenario, interval, dates):
    config = {"symbol": {"symbol": "NVDA", "exchange": "NASDAQ"}, "start_date": dates[0],
              "end_date": dates[1], "interval": interval}
    graph, fixture, expected = _case(scenario, "OverseasStockHistoricalDataNode", config)
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert _stable(result.outputs["read"]["values"]) == _stable(expected)
    assert result.outputs["read"]["interval"] == interval
    if interval == "15m":
        assert result.outputs["read"]["value"]["time_series"][0]["date"] == "20261016093000"


@pytest.mark.asyncio
async def test_korea_ranking_node_runs_t1463_from_the_tape():
    config = {"ranking_type": "trading_value", "market": "KOSPI", "limit": 2}
    graph, fixture, expected = _case("korea_stock_ranking_trading_value", "KoreaStockRankingNode", config)
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["read"]["rankings"] == expected["rankings"]
    assert [s["symbol"] for s in result.outputs["read"]["symbols"]] == ["005930", "000660"]


@pytest.mark.asyncio
async def test_quote_and_futures_contract_nodes_run_from_the_tape():
    graph, fixture, expected = _case("overseas_stock_quote", "OverseasStockMarketDataNode",
                                     {"symbol": {"symbol": "NVDA", "exchange": "NASDAQ"}})
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["read"] == expected and result.outputs["read"]["values"][0]["price"] == 180.0
    graph, fixture, expected = _case("futures_contract_front", "FuturesContractNode",
                                     {"base_products": ["MES"], "contract_selection": "front",
                                      "futures_exchange": "CME"})
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["read"] == expected
    assert result.outputs["read"]["symbols"] == [{"exchange": "CME", "symbol": "MESZ26"}]


@pytest.mark.asyncio
async def test_a_linked_futures_credential_reference_resolves_to_the_placeholder():
    """ContractInfo requires the exact linked broker credential; under a tape it is the placeholder."""
    data = SCENARIOS["futures_contract_info_linked"]
    connection = {"product": "overseas_futures", "provider": "ls-sec.co.kr", "paper_trading": True,
                  "broker_node_id": "broker", "credential_id": "futures-cred"}
    graph = {"id": "tape", "name": "Tape", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasFuturesBrokerNode", "paper_trading": True, "credential_id": "futures-cred"},
        {"id": "read", "type": "OverseasFuturesContractInfoNode", "symbol": {"symbol": "MESZ26", "exchange": "CME"}}],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "read"}],
        "credentials": [{"credential_id": "futures-cred", "type": "broker_ls_overseas_futures", "data": []}]}
    fixture = {"as_of": AS_OF, "nodes": {
        "broker": recording("OverseasFuturesBrokerNode", {"paper_trading": True, "credential_id": "futures-cred"},
                            {"connection": connection}, {"type": "object", "required": ["connection"]}, as_of=AS_OF),
        "read": {"kind": "ls_tape", "as_of": AS_OF, "tape": deepcopy(data["tape"])}}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert _stable(result.outputs["read"]) == _stable(data["expected"])
    assert result.outputs["read"]["verified"] is True


@pytest.mark.asyncio
async def test_a_request_the_tape_does_not_answer_names_the_tr():
    config = {"symbol": {"symbol": "TSLA", "exchange": "NASDAQ"}, "start_date": "20261015",
              "end_date": "20261016", "interval": "15m"}
    graph, fixture, _ = _case("overseas_stock_minute_bars_15m", "OverseasStockHistoricalDataNode", config)
    result = await replay(graph, fixture)
    assert not result.passed
    error = next(e for e in result.errors if e["code"] == "REPLAY_FIXTURE_REQUIRED")
    assert "g3203" in error["message"] and "g3203InBlock.symbol" in error["detail"]["misses"][0]["differing"]


@pytest.mark.asyncio
async def test_ignore_lists_only_the_wall_clock_fields():
    graph, fixture, expected = _case("overseas_stock_account_holding", "OverseasStockAccountNode")
    entry = fixture["nodes"]["read"]["tape"][0]
    assert entry["ignore"] == ["COSOQ00201InBlock1.BaseDt"]
    entry["request"]["COSOQ00201InBlock1"]["BaseDt"] = "19990101"  # the date the author saw is irrelevant
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    entry.pop("ignore")
    result = await replay(graph, fixture)
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_REQUIRED" for e in result.errors)


@pytest.mark.asyncio
async def test_a_token_failure_answer_is_never_followed_by_a_reissue():
    graph, fixture, _ = _case("korea_stock_open_orders_empty", "KoreaStockOpenOrdersNode")
    entry = fixture["nodes"]["read"]["tape"][0]
    entry["status"], entry["json"] = 500, {"rsp_cd": "IGW00121", "rsp_msg": "유효하지 않은 토큰입니다."}
    result = await replay(graph, fixture)
    assert not result.passed
    blocked = next(e for e in result.errors if e["code"] == "REPLAY_CAPABILITY_BLOCKED")
    assert "token_reissue" in blocked["message"]


@pytest.mark.asyncio
async def test_a_tape_cannot_serve_a_non_read_node():
    graph = {"id": "t", "name": "t", "nodes": [{"id": "start", "type": "StartNode"},
             {"id": "notify", "type": "TelegramNode", "template": "x"}],
             "edges": [{"from": "start", "to": "notify"}]}
    fixture = {"as_of": AS_OF, "nodes": {"notify": {"kind": "ls_tape", "as_of": AS_OF, "tape": [
        {"tr": "t0425", "request": {}, "json": {}}]}}}
    result = await replay(graph, fixture)
    assert not result.passed
    assert any(e["code"] == "REPLAY_CAPABILITY_BLOCKED" for e in result.errors)


@pytest.mark.asyncio
async def test_a_tape_is_bound_to_the_shared_clock():
    graph, fixture, _ = _case("korea_stock_open_orders_empty", "KoreaStockOpenOrdersNode")
    fixture["nodes"]["read"]["as_of"] = "2026-10-15T14:00:00Z"
    result = await replay(graph, fixture)
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors)


@pytest.mark.asyncio
async def test_another_task_in_the_same_loop_never_sees_the_tape():
    from programgarden_finance.ls.replay_transport import active_transport
    seen = []
    stop = asyncio.Event()

    async def watcher():
        while not stop.is_set():
            seen.append(active_transport())
            await asyncio.sleep(0)

    graph, fixture, expected = _case("overseas_futures_account_holding", "OverseasFuturesAccountNode")
    task = asyncio.create_task(watcher())
    try:
        result = await replay(graph, fixture)
    finally:
        stop.set()
        await task
    assert result.passed, result.errors
    assert seen and all(value is None for value in seen)
    assert active_transport() is None

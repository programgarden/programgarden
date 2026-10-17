"""Per-item recordings inside a SplitNode branch (a basket of symbols).

The branch runner executes each item with ``_branch_scope = "<split>#<index>"``
and no auto-iteration context. A per-item recording group is selected by the
split item read from the split's ``items`` port at that index (never from the
split's single ``item`` slot, which parallel branches overwrite). A flat
recording keeps its meaning: one request for every item, ``item`` null.
"""
import pytest

from programgarden.replay_external import per_item_key, recording, request_identity
from programgarden.validation_replay import content_hash, replay

AS_OF = "2026-09-22T14:00:00Z"
CONNECTION = {"product": "overseas_stock", "provider": "ls-sec.co.kr"}
BASKET = [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "XOM", "exchange": "NYSE"},
          {"symbol": "NVDA", "exchange": "NASDAQ"}]
PRICES = {"AAPL": 190.0, "XOM": 110.0, "NVDA": 180.0}
QUOTE_CONTRACT = {"type": "object", "required": ["values"]}


def _graph(*, parallel=False, branch_tail=()):
    nodes = [{"id": "start", "type": "StartNode"},
             {"id": "broker", "type": "OverseasStockBrokerNode"},
             {"id": "wl", "type": "WatchlistNode", "symbols": BASKET},
             {"id": "split", "type": "SplitNode", "parallel": parallel},
             {"id": "quote", "type": "OverseasStockMarketDataNode", "symbol": "{{ nodes.split.item }}"},
             {"id": "calc", "type": "CodeNode", "outputs": [{"name": "result", "type": "number"}],
              "data": "{{ nodes.quote.values[0].price }}",
              "code": "def execute(data, params, context):\n return {'result': data * 2}"},
             *branch_tail,
             {"id": "agg", "type": "AggregateNode", "mode": "collect"}]
    chain = [n["id"] for n in nodes]
    return {"id": "basket", "name": "Basket", "nodes": nodes,
            "edges": [{"from": a, "to": b} for a, b in zip(chain, chain[1:])]}


def _quote(item, price=None):
    value = {**item, "price": PRICES[item["symbol"]] if price is None else price}
    return recording("OverseasStockMarketDataNode", {"symbol": item, "connection": CONNECTION},
                     {"values": [value]}, QUOTE_CONTRACT, as_of=AS_OF, item=item)


def _fixture(quote_group):
    return {"as_of": AS_OF, "nodes": {
        "broker": recording("OverseasStockBrokerNode", {}, {"connection": CONNECTION},
                            {"type": "object", "required": ["connection"]}, as_of=AS_OF),
        "quote": quote_group}}


def _group(items=BASKET):
    return {"items": {per_item_key("OverseasStockMarketDataNode", item): _quote(item) for item in items}}


@pytest.mark.asyncio
@pytest.mark.parametrize("parallel", [False, True])
async def test_each_basket_item_reads_its_own_recording(parallel):
    result = await replay(_graph(parallel=parallel), _fixture(_group()))
    assert result.passed, result.errors
    collected = result.outputs["agg"]["array"]
    assert sorted(collected) == sorted(PRICES[i["symbol"]] * 2 for i in BASKET)
    assert result.executed.count("quote") == 3 and result.executed.count("calc") == 3


@pytest.mark.asyncio
async def test_missing_item_recording_is_required_not_guessed():
    result = await replay(_graph(), _fixture(_group(BASKET[:2])))
    assert not result.passed
    error = next(e for e in result.errors if e["code"] == "REPLAY_FIXTURE_REQUIRED")
    assert "NASDAQ:NVDA" in error["message"] and "split#2" in error["message"]


@pytest.mark.asyncio
async def test_a_recording_for_another_item_is_a_mismatch():
    group = _group()
    # The NYSE:XOM slot holds a recording made for AAPL: the bound item differs.
    group["items"]["NYSE:XOM"] = _quote(BASKET[0])
    result = await replay(_graph(), _fixture(group))
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors), result.errors


@pytest.mark.asyncio
async def test_flat_recording_still_serves_a_one_item_split():
    """The single-item split mirror records a flat recording (item null)."""
    graph = _graph()
    graph["nodes"][2]["symbols"] = BASKET[:1]
    flat = recording("OverseasStockMarketDataNode", {"symbol": BASKET[0], "connection": CONNECTION},
                     {"values": [{**BASKET[0], "price": 190.0}]}, QUOTE_CONTRACT, as_of=AS_OF)
    result = await replay(graph, _fixture(flat))
    assert result.passed, result.errors
    assert result.outputs["agg"]["array"] == [380.0]


@pytest.mark.asyncio
async def test_flat_recording_cannot_serve_a_basket_with_other_requests():
    flat = recording("OverseasStockMarketDataNode", {"symbol": BASKET[0], "connection": CONNECTION},
                     {"values": [{**BASKET[0], "price": 190.0}]}, QUOTE_CONTRACT, as_of=AS_OF)
    result = await replay(_graph(), _fixture(flat))
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors), result.errors


@pytest.mark.asyncio
async def test_basket_orders_one_per_item_from_the_simulation_book():
    order = {"id": "order", "type": "OverseasStockNewOrderNode", "side": "buy", "order_type": "limit",
             "order": {"symbol": "{{ nodes.split.item.symbol }}", "exchange": "{{ nodes.split.item.exchange }}",
                       "quantity": 1, "price": "{{ nodes.quote.values[0].price }}"}}
    graph = _graph(parallel=True, branch_tail=(order,))
    fixture = _fixture(_group())
    fixture["broker"] = {"as_of": AS_OF, "account": {"cash": 1000, "currency": "USD", "max_investment": 1000, "positions": {}},
                         "instruments": {f"{i['exchange']}:{i['symbol']}": {
                             "product": "overseas_stock", "currency": "USD", "price": PRICES[i["symbol"]],
                             "as_of": AS_OF, "session_open": True, "tradeable": True, "tick_size": 0.01,
                             "max_age_seconds": 60} for i in BASKET}}
    fixture["orders"] = {"order": {"response": "filled"}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.simulation["positions"] == {"NASDAQ:AAPL": 1, "NYSE:XOM": 1, "NASDAQ:NVDA": 1}
    assert result.simulation["cash"] == pytest.approx(1000 - sum(PRICES.values()))


def test_per_item_key_rules():
    assert per_item_key("OverseasStockMarketDataNode", {"symbol": "AAPL", "exchange": "NASDAQ"}) == "NASDAQ:AAPL"
    assert per_item_key("KoreaStockMarketDataNode", {"symbol": "005930"}) == "KRX:005930"
    # An overseas row without an exchange and any non-symbol item are keyed by content.
    row = {"symbol": "AAPL", "quantity": 3}
    assert per_item_key("OverseasStockAccountNode", row) == content_hash(row)
    assert per_item_key("HTTPRequestNode", "SPY") == content_hash("SPY")


@pytest.mark.asyncio
async def test_non_symbol_items_select_by_content():
    series = ["DGS10", "DGS2"]
    http = {"id": "http", "type": "HTTPRequestNode", "method": "GET",
            "url": "https://fixture.invalid/series", "query_params": {"id": "{{ nodes.split.item }}"}}
    graph = {"id": "series", "name": "Series", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "src", "type": "CodeNode", "outputs": [{"name": "values", "type": "array"}],
         "code": f"def execute(data, params, context):\n return {{'values': {series!r}}}"},
        {"id": "split", "type": "SplitNode", "array": "{{ nodes.src.values }}"}, http,
        {"id": "agg", "type": "AggregateNode", "mode": "collect"}],
        "edges": [{"from": "start", "to": "src"}, {"from": "src", "to": "split"},
                  {"from": "split", "to": "http"}, {"from": "http", "to": "agg"}]}
    contract = {"type": "object", "required": ["response"]}
    group = {"items": {per_item_key("HTTPRequestNode", s): recording(
        "HTTPRequestNode", {**{k: v for k, v in http.items() if k not in ("id", "type")},
                            "query_params": {"id": s}},
        {"response": {"series": s, "value": 4.0 if s == "DGS10" else 3.5}}, contract,
        as_of=AS_OF, item=s) for s in series}}
    result = await replay(graph, {"as_of": AS_OF, "nodes": {"http": group}})
    assert result.passed, result.errors
    assert sorted(r["series"] for r in result.outputs["agg"]["array"]) == ["DGS10", "DGS2"]
    assert request_identity("HTTPRequestNode", {"method": "GET", "url": "https://fixture.invalid/series",
                                                "query_params": {"id": "DGS2"}})

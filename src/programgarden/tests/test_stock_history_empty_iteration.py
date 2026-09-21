"""Regressions for exchange-scoped charts and item-bound empty filtered orders."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import (
    BrokerNodeExecutor,
    HistoricalDataNodeExecutor,
    NewOrderNodeExecutor,
    WorkflowExecutor,
)


@pytest.mark.parametrize(
    "exchange,symbol,code",
    [("NYSE", "XOM", "81"), ("NYSE", "CVX", "81"),
     ("NASDAQ", "AAPL", "82"), ("AMEX", "SPY", "81")],
)
async def test_historical_request_keeps_selected_exchange(tmp_path, exchange, symbol, code):
    requests = []

    def query(*, body):
        requests.append(body)
        bar = SimpleNamespace(date="20260918", open=10, high=12, low=9, close=11, volume=100)
        return SimpleNamespace(req_async=AsyncMock(return_value=SimpleNamespace(block1=[bar])))

    client = SimpleNamespace(
        overseas_stock=lambda: SimpleNamespace(chart=lambda: SimpleNamespace(g3204=query)),
    )
    context = ExecutionContext("fixture", "workflow-fixture", storage_dir=str(tmp_path))
    context.get_credential = lambda: {
        "appkey": "synthetic", "appsecret": "synthetic", "paper_trading": False,
    }
    with patch("programgarden.executor.ensure_ls_login", return_value=(client, True, None)):
        output = await HistoricalDataNodeExecutor().execute(
            "history", "OverseasStockHistoricalDataNode", {
                "symbols": [{"symbol": symbol, "exchange": exchange}],
                "start_date": "20260723", "end_date": "20260921", "interval": "1d",
                "connection": {"product": "overseas_stock"},
            }, context,
        )
    assert len(requests) == 1
    assert requests[0].exchcd == code
    assert requests[0].keysymbol == code + symbol
    assert len(output["value"]["time_series"]) == 1


@pytest.mark.parametrize(
    "held,expected",
    [([], 0), ([{"symbol": "XOM", "exchange": "NYSE", "quantity": 2}], 1)],
)
async def test_filtered_orders_need_an_iteration_item(tmp_path, held, expected):
    calls = []

    async def broker(self, node_id, node_type, config, context, **kwargs):
        return {"connection": {
            "product": "overseas_stock", "paper_trading": False, "credential_id": "fixture",
        }}

    async def order(self, node_id, node_type, config, context, **kwargs):
        calls.append(config["order"])
        return {"order_id": "intercepted", "order_result": {"success": True}}

    workflow = {
        "id": "empty-filter-fixture", "name": "Empty filter fixture",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "fixture"},
            {"id": "pick", "type": "SymbolFilterNode", "operation": "intersection",
             "input_a": held, "input_b": [{"symbol": "XOM", "exchange": "NYSE"}]},
            {"id": "sell", "type": "OverseasStockNewOrderNode", "side": "sell",
             "order_type": "market", "order": {
                 "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
                 "quantity": "{{ item.quantity }}",
             }},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "pick"},
            {"from": "pick", "to": "sell"},
        ],
        "credentials": [{
            "credential_id": "fixture", "type": "broker_ls_overseas_stock", "data": [
                {"key": "appkey", "value": "synthetic", "type": "password"},
                {"key": "appsecret", "value": "synthetic", "type": "password"},
            ],
        }],
    }
    with (
        patch.object(BrokerNodeExecutor, "execute", broker),
        patch.object(NewOrderNodeExecutor, "execute", order),
    ):
        job = await WorkflowExecutor().execute(workflow, storage_dir=str(tmp_path))
        await asyncio.wait_for(job._task, 20)
    assert job.status == "completed"
    assert len(calls) == expected
    if expected:
        assert calls == [{"symbol": "XOM", "exchange": "NYSE", "quantity": 2}]
    else:
        assert job.context.get_all_outputs("sell")["skipped_by"] == "no_upstream_signal"

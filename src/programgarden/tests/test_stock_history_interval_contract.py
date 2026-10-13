"""Unsupported stock periods must not become mislabeled daily broker data."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from programgarden.executor import HistoricalDataNodeExecutor, WorkflowExecutor
from programgarden_core.nodes.backtest_stock import OverseasStockHistoricalDataNode


SUPPORTED = {"1d": "2", "1w": "3", "1M": "4", "1Y": "5"}
UNSUPPORTED = ("1m", "5m", "15m", "1h", "1min", "", "daily", None, [])


@pytest.mark.parametrize("interval", [*SUPPORTED, *UNSUPPORTED])
def test_public_validation_reports_exact_interval_error(interval):
    workflow = {
        "id": "stock-history-contract", "name": "Synthetic stock history", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "fixture"},
            {"id": "history", "type": "OverseasStockHistoricalDataNode", "interval": interval,
             "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
        ],
        "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "history"}],
        "credentials": [{"credential_id": "fixture", "type": "broker_ls_overseas_stock", "data": []}],
    }
    result = WorkflowExecutor().validate(workflow)
    errors = [error for error in result.errors if error.location.field_path == "interval"]
    if isinstance(interval, str) and interval in SUPPORTED:
        assert result.is_valid, result.errors
        assert not errors
    else:
        assert len(errors) == 1
        assert errors[0].code == "INVALID_FIELD_ENUM"
        assert errors[0].location.node_id == "history"
        assert errors[0].available_values == list(SUPPORTED)


@pytest.mark.parametrize("interval", UNSUPPORTED)
def test_schema_rejects_unsupported_periods(interval):
    with pytest.raises(ValidationError):
        OverseasStockHistoricalDataNode(id="history", interval=interval)


@pytest.mark.parametrize("interval", UNSUPPORTED)
async def test_direct_fetch_rejects_before_credentials_or_login(interval):
    context = Mock()
    with patch("programgarden.executor.ensure_ls_login") as login:
        with pytest.raises(ValueError, match="UNSUPPORTED_STOCK_HISTORY_INTERVAL"):
            await HistoricalDataNodeExecutor()._fetch_overseas_stock(
                ["AAPL"], "20261001", "20261002", interval, context, "history"
            )
    context.get_credential.assert_not_called()
    login.assert_not_called()


@pytest.mark.parametrize("deep_validate", [False, True])
@pytest.mark.parametrize("node_type", ["OverseasStockHistoricalDataNode", "HistoricalDataNode"])
async def test_execute_and_deep_validation_cannot_fabricate_intraday_data(deep_validate, node_type):
    context = Mock(is_deep_validate=deep_validate)
    with patch("programgarden.executor.ensure_ls_login") as login:
        with pytest.raises(ValueError, match="UNSUPPORTED_STOCK_HISTORY_INTERVAL"):
            await HistoricalDataNodeExecutor().execute(
                "history", node_type, {"interval": "1m"}, context
            )
    context.get_output.assert_not_called()
    context.get_credential.assert_not_called()
    login.assert_not_called()


@pytest.mark.parametrize("deep_validate", [False, True])
@pytest.mark.parametrize("product", ["overseas_futureoption", "overseas_futures"])
async def test_legacy_futures_intraday_remains_available(deep_validate, product):
    context = Mock(is_deep_validate=deep_validate, _iteration_item=None)
    context.get_output.return_value = None
    context.get_deep_fixture.return_value = None
    config = {"interval": "1m", "connection": {"product": product},
              "symbol": {"symbol": "SYNTHETIC", "exchange": "HKEX"},
              "start_date": "20261001", "end_date": "20261002"}
    executor = HistoricalDataNodeExecutor()
    with patch.object(executor, "_fetch_overseas_futures", new_callable=AsyncMock,
                      return_value=[]) as fetch, \
         patch("programgarden.executor.ensure_ls_login") as login:
        output = await executor.execute("history", "HistoricalDataNode", config, context)
    assert output["interval"] == "1m"
    if deep_validate:
        fetch.assert_not_awaited()
    else:
        fetch.assert_awaited_once()
        assert fetch.call_args.args[3] == "1m"
    login.assert_not_called()


@pytest.mark.parametrize("interval,gubun", SUPPORTED.items())
async def test_supported_periods_keep_exact_g3204_request_and_output(interval, gubun):
    node = OverseasStockHistoricalDataNode(id="history", interval=interval)
    requests = []
    async def response():
        return SimpleNamespace(block1=[SimpleNamespace(
            date="20261001", open=10, high=12, low=9, close=11, volume=100
        )])
    def g3204(*, body):
        requests.append(body)
        return SimpleNamespace(req_async=response)
    client = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(
        chart=lambda: SimpleNamespace(g3204=g3204)
    ))
    context = Mock()
    context.get_credential.return_value = {"appkey": "synthetic", "appsecret": "synthetic"}
    with patch("programgarden.executor.ensure_ls_login", return_value=(client, True, None)):
        output = await HistoricalDataNodeExecutor()._fetch_overseas_stock(
            ["AAPL"], "20261001", "20261002", node.interval, context, "history",
            symbol_exchange_map={"AAPL": "82"}
        )
    assert len(requests) == 1
    assert requests[0].gubun == gubun
    assert requests[0].sdate == "20261001"
    assert requests[0].edate == "20261002"
    assert output == [{"symbol": "AAPL", "exchange": "NASDAQ", "time_series": [
        {"date": "20261001", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 100}
    ]}]


def test_authoring_catalog_and_examples_match_supported_periods():
    assert OverseasStockHistoricalDataNode(id="history").interval == "1d"
    schema = OverseasStockHistoricalDataNode.get_field_schema()["interval"]
    assert schema.enum_values == list(SUPPORTED)
    assert set(OverseasStockHistoricalDataNode.model_json_schema()["properties"]["interval"]["enum"]) == set(SUPPORTED)
    for example in OverseasStockHistoricalDataNode._examples:
        for node in example["workflow_snippet"]["nodes"]:
            if node["type"] == "OverseasStockHistoricalDataNode":
                assert node.get("interval", "1d") in SUPPORTED
    root = Path(__file__).resolve().parents[2]
    for lang in ("en", "ko"):
        locale = json.loads((root / f"core/programgarden_core/i18n/locales/{lang}.json").read_text())
        for label in schema.enum_labels.values():
            assert label.removeprefix("i18n:") in locale

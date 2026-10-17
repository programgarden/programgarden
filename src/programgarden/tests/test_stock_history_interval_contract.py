"""Stock history intervals: g3204 periods, g3203 minute bars, and nothing mislabeled.

2.7.0 connects LS g3203 for 1m/5m/10m/15m/30m/60m. Each ncnt answered rsp_cd
00000 with bars of exactly that step on one live platform call (2026-10-18).
Unknown values are still refused before credentials or login.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from programgarden.executor import HistoricalDataNodeExecutor, WorkflowExecutor
from programgarden_core.nodes.backtest_stock import OverseasStockHistoricalDataNode


PERIODS = {"1d": "2", "1w": "3", "1M": "4", "1Y": "5"}
MINUTES = {"1m": 1, "5m": 5, "10m": 10, "15m": 15, "30m": 30, "60m": 60}
SUPPORTED = {**PERIODS, **MINUTES}
UNSUPPORTED = ("1h", "1min", "2m", "120m", "30s", "", "daily", None, [])


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
async def test_execute_and_deep_validation_cannot_fabricate_unknown_intervals(deep_validate, node_type):
    context = Mock(is_deep_validate=deep_validate)
    with patch("programgarden.executor.ensure_ls_login") as login:
        with pytest.raises(ValueError, match="UNSUPPORTED_STOCK_HISTORY_INTERVAL"):
            await HistoricalDataNodeExecutor().execute(
                "history", node_type, {"interval": "1h"}, context
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


@pytest.mark.parametrize("interval,gubun", PERIODS.items())
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


def test_localized_stock_interval_does_not_change_futures_contract():
    root = Path(__file__).resolve().parents[2]
    stock_key = "fields.OverseasStockHistoricalDataNode.interval"
    futures_key = "fields.OverseasFuturesHistoricalDataNode.interval"
    for lang in ("en", "ko"):
        locale = json.loads((root / f"core/programgarden_core/i18n/locales/{lang}.json").read_text())
        assert "g3204" in locale[stock_key]
        assert "g3204" not in locale[futures_key]
        assert "1m" in locale[futures_key]
    assert not any("daily (or intraday)" in text for text in OverseasStockHistoricalDataNode._usage["when_to_use"])


def _g3203_client(requests, rows, error_msg=None):
    async def response():
        return SimpleNamespace(block1=rows, error_msg=error_msg)
    def g3203(*, body):
        requests.append(body)
        return SimpleNamespace(req_async=response)
    def g3204(*, body):  # pragma: no cover - a minute interval never reads g3204
        raise AssertionError("minute interval must not read g3204")
    return SimpleNamespace(overseas_stock=lambda: SimpleNamespace(
        chart=lambda: SimpleNamespace(g3203=g3203, g3204=g3204)))


def _row(date, loctime, close, exevol):
    # Field types of finance G3203OutBlock1 as LS returns them (close is text).
    return SimpleNamespace(date=date, loctime=loctime, open=close - 0.5, high=close + 1,
                           low=close - 1, close=f"{close:.4f}", exevol=exevol, amount=0)


@pytest.mark.parametrize("interval,ncnt", MINUTES.items())
async def test_minute_intervals_send_one_exact_g3203_request(interval, ncnt):
    node = OverseasStockHistoricalDataNode(id="history", interval=interval)
    requests = []
    # LS answers ascending rows; feed them out of order to prove the sort.
    rows = [_row("20261016", "180000", 214.27, 8475), _row("20261016", "081500", 217.27, 31186)]
    context = Mock()
    context.get_credential.return_value = {"appkey": "synthetic", "appsecret": "synthetic"}
    with patch("programgarden.executor.ensure_ls_login", return_value=(_g3203_client(requests, rows), True, None)):
        output = await HistoricalDataNodeExecutor()._fetch_overseas_stock(
            ["NVDA"], "20261015", "20261016", node.interval, context, "history",
            symbol_exchange_map={"NVDA": "82"})
    assert len(requests) == 1
    body = requests[0]
    assert (body.keysymbol, body.exchcd, body.symbol) == ("82NVDA", "82", "NVDA")
    assert (body.ncnt, body.qrycnt, body.sdate, body.edate) == (ncnt, 500, "20261015", "20261016")
    assert (body.cts_date, body.cts_time, body.delaygb, body.comp_yn) == ("", "", "R", "N")
    assert output == [{"symbol": "NVDA", "exchange": "NASDAQ", "time_series": [
        {"date": "20261016081500", "open": 216.77, "high": 218.27, "low": 216.27, "close": 217.27, "volume": 31186},
        {"date": "20261016180000", "open": 213.77, "high": 215.27, "low": 213.27, "close": 214.27, "volume": 8475},
    ]}]


async def test_minute_broker_error_is_an_empty_series_not_daily_bars():
    requests = []
    context = Mock()
    context.get_credential.return_value = {"appkey": "synthetic", "appsecret": "synthetic"}
    with patch("programgarden.executor.ensure_ls_login",
               return_value=(_g3203_client(requests, [], error_msg="synthetic failure"), True, None)):
        output = await HistoricalDataNodeExecutor()._fetch_overseas_stock(
            ["NVDA"], "20261015", "20261016", "15m", context, "history", symbol_exchange_map={"NVDA": "82"})
    assert len(requests) == 1
    assert output == [{"symbol": "NVDA", "exchange": "NASDAQ", "time_series": []}]


def test_g3204_selector_still_refuses_minute_intervals():
    with pytest.raises(ValueError, match="g3203 minute interval"):
        HistoricalDataNodeExecutor._stock_history_gubun("15m")
    assert HistoricalDataNodeExecutor._stock_history_request("15m") == ("g3203", 15)
    assert HistoricalDataNodeExecutor._stock_history_request("1d") == ("g3204", "2")


async def test_deep_validation_minute_fixture_has_minute_stamps():
    context = Mock(is_deep_validate=True, _iteration_item=None)
    context.get_output.return_value = None
    context.get_deep_fixture.return_value = None
    config = {"interval": "15m", "symbol": {"symbol": "NVDA", "exchange": "NASDAQ"}}
    with patch("programgarden.executor.ensure_ls_login") as login:
        output = await HistoricalDataNodeExecutor().execute(
            "history", "OverseasStockHistoricalDataNode", config, context)
    login.assert_not_called()
    dates = [bar["date"] for bar in output["value"]["time_series"]]
    assert all(len(d) == 14 for d in dates)
    assert dates[1][8:12] == "0945" and dates[0][8:12] == "0930"

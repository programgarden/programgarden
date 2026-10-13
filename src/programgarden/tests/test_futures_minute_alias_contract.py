"""Preserve one-page futures requests while rejecting daily misrouting."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from programgarden.executor import HistoricalDataNodeExecutor, WorkflowExecutor
from programgarden.futures_history import DAILY_INTERVALS, INTERVAL_ALIASES, MINUTE_INTERVALS
from programgarden_core.nodes.backtest_futures import OverseasFuturesHistoricalDataNode as Node
from programgarden_core.registry.node_registry import NodeTypeRegistry
from programgarden_finance.ls.overseas_futureoption.chart.o3103.blocks import (
    O3103InBlock, O3103OutBlock, O3103OutBlock1, O3103Response, O3103ResponseHeader,
)

PERIODS = {**MINUTE_INTERVALS, **{alias: MINUTE_INTERVALS[value] for alias, value in INTERVAL_ALIASES.items()}}
INVALID = ["1h", "3m", "60min", "daily", "", None, []]


@pytest.fixture(autouse=True)
def no_external_broker(monkeypatch):
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", Mock(side_effect=AssertionError("No broker login")))


def workflow(**fields):
    return {"id": "synthetic-futures-history", "name": "Synthetic futures history",
            "nodes": [{"id": "start", "type": "StartNode"},
                      {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fixture"},
                      {"id": "history", "type": "OverseasFuturesHistoricalDataNode", **fields}],
            "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "history"}],
            "credentials": [{"credential_id": "fixture", "type": "broker_ls_overseas_futures", "data": []}]}


def minute_api():
    # More data exists; the inherited contract still makes exactly one request.
    response = O3103Response(status_code=200, rsp_cd="00000", rsp_msg="",
        header=O3103ResponseHeader(content_type="application/json", tr_cd="o3103", tr_cont="Y", tr_cont_key="synthetic-next"),
        block=O3103OutBlock(shcode="SYNTHETIC", readcnt=200, cts_date="20261012", cts_time="120000"),
        block1=[O3103OutBlock1(date="20261013", time=time, open=10, high=12, low=9, close=11, volume=10)
                for time in ["120000", "115500"]])
    request = SimpleNamespace(req_async=AsyncMock(return_value=response))
    chart = SimpleNamespace(o3103=Mock(return_value=request), o3108=Mock(side_effect=AssertionError("No daily substitution")))
    return SimpleNamespace(chart=lambda: chart), chart, request


@pytest.mark.parametrize("interval,ncnt", PERIODS.items())
async def test_canonical_and_legacy_periods_use_identical_single_page_requests(monkeypatch, interval, ncnt):
    api, chart, request = minute_api()
    monkeypatch.setattr("programgarden.executor.ensure_ls_login", lambda *a, **k: (SimpleNamespace(overseas_futureoption=lambda: api), True, None))
    context = Mock(is_deep_validate=False, _iteration_item=None)
    context.get_output.return_value = None
    context.get_credential.return_value = {"appkey": "synthetic", "appsecret": "synthetic"}
    output = await HistoricalDataNodeExecutor().execute("history", "OverseasFuturesHistoricalDataNode",
        {"interval": interval, "adjust": False, "start_date": "20200101", "end_date": "20200102",
         "symbol": {"symbol": "SYNTHETIC", "exchange": "HKEX"}, "connection": {"product": "overseas_futures"}}, context)
    body = chart.o3103.call_args.kwargs["body"]
    assert body.model_dump() == {"shcode": "SYNTHETIC", "ncnt": ncnt, "readcnt": 200, "cts_date": "", "cts_time": ""}
    request.req_async.assert_awaited_once()
    chart.o3108.assert_not_called()
    assert output["value"]["exchange"] == "HKEX"
    assert [row["date"] for row in output["value"]["time_series"]] == ["20261013115500", "20261013120000"]
    # Existing period is a request label; these dates were never sent to o3103.
    assert output["period"] == "20200101~20200102"
    assert output["interval"] == interval


@pytest.mark.parametrize("interval", [*PERIODS, *DAILY_INTERVALS])
def test_valid_saved_periods_and_native_model_aliases_remain_accepted(interval):
    result = WorkflowExecutor().validate(workflow(interval=interval, adjust=False))
    assert result.is_valid, result.errors
    assert Node(id="history", interval=interval).interval == INTERVAL_ALIASES.get(interval, interval)


@pytest.mark.parametrize("interval", INVALID)
def test_unsupported_periods_have_native_and_public_errors(interval):
    with pytest.raises(ValidationError):
        Node(id="history", interval=interval)
    result = WorkflowExecutor().validate(workflow(interval=interval))
    errors = [error for error in result.errors if error.location.field_path == "interval"]
    assert len(errors) == 1 and errors[0].code == "INVALID_FIELD_ENUM"


@pytest.mark.parametrize("interval", INVALID)
async def test_invalid_direct_period_fails_before_credentials(interval):
    context = Mock()
    with pytest.raises(ValueError, match="UNSUPPORTED_FUTURES_HISTORY_INTERVAL"):
        await HistoricalDataNodeExecutor()._fetch_overseas_futures(["SYNTHETIC"], "20261001", "20261013", interval, context, "history")
    context.get_credential.assert_not_called()


@pytest.mark.parametrize("deep", [False, True])
@pytest.mark.parametrize("node_type,product", [("OverseasFuturesHistoricalDataNode", "overseas_futures"),
    ("HistoricalDataNode", "overseas_futures"), ("HistoricalDataNode", "overseas_futureoption")])
@pytest.mark.parametrize("fields,error", [({"interval": "1h"}, "UNSUPPORTED_FUTURES_HISTORY_INTERVAL"),
                                       ({"adjust": True}, "FUTURES_HISTORY_ADJUST_UNSUPPORTED")])
async def test_invalid_claims_fail_before_credentials_or_deep_fixtures(deep, node_type, product, fields, error):
    context = Mock(is_deep_validate=deep)
    with pytest.raises(ValueError, match=error):
        await HistoricalDataNodeExecutor().execute("history", node_type,
            {"interval": "1m", "connection": {"product": product}, **fields}, context)
    context.get_credential.assert_not_called()
    context.get_output.assert_not_called()


@pytest.mark.parametrize("interval,gubun", DAILY_INTERVALS.items())
async def test_daily_weekly_monthly_requests_are_unchanged(interval, gubun):
    request = SimpleNamespace(req_async=AsyncMock(return_value=SimpleNamespace(block1=[], rsp_msg="")))
    chart = SimpleNamespace(o3108=Mock(return_value=request))
    result = await HistoricalDataNodeExecutor()._fetch_futures_daily_chart(
        SimpleNamespace(chart=lambda: chart), "SYNTHETIC", "20261001", "20261013", interval, Mock(), "history")
    assert result == []
    body = chart.o3108.call_args.kwargs["body"]
    assert (body.shcode, body.gubun, body.qrycnt, body.sdate, body.edate) == ("SYNTHETIC", gubun, 200, "20261001", "20261013")
    request.req_async.assert_awaited_once()


@pytest.mark.parametrize("adjust", [False, True, "{{ nodes.flag.value }}"])
def test_adjust_false_is_preserved_but_unimplemented_adjustment_is_rejected(adjust):
    result = WorkflowExecutor().validate(workflow(interval="1d", adjust=adjust))
    if adjust is False:
        assert result.is_valid
        assert Node(id="history", adjust=False).model_dump()["adjust"] is False
    else:
        assert not result.is_valid
        with pytest.raises(ValidationError):
            Node(id="history", adjust=adjust)
    assert WorkflowExecutor().validate(workflow(interval="1d")).is_valid


def test_catalog_keeps_truthful_false_metadata_and_exact_sdk_fields():
    schema = Node.get_field_schema()
    assert schema["interval"].enum_values == [*MINUTE_INTERVALS, *DAILY_INTERVALS]
    assert schema["adjust"].default is False and schema["adjust"].example is False
    assert schema["adjust"].expression_mode == "fixed_only"
    assert Node.model_json_schema()["properties"]["adjust"]["const"] is False
    assert Node.as_tool_schema()["parameters"]["adjust"]["default"] is False
    for language in ("en", "ko"):
        exported = NodeTypeRegistry().get_schema("OverseasFuturesHistoricalDataNode", language).config_schema
        assert exported["interval"]["enum_values"] == schema["interval"].enum_values
        assert exported["adjust"]["default"] is False
        assert exported["adjust"]["expression_mode"] == "fixed_only"
        assert "error" not in exported["adjust"]
    assert {"shcode", "ncnt", "readcnt", "cts_date", "cts_time"} == set(O3103InBlock.model_fields)
    assert {"date", "time", "open", "high", "low", "close", "volume"} <= set(O3103OutBlock1.model_fields)
    root = Path(__file__).resolve().parents[2]
    for language in ("en", "ko"):
        locale = json.loads((root / f"core/programgarden_core/i18n/locales/{language}.json").read_text())
        assert all(label.removeprefix("i18n:") in locale for label in schema["interval"].enum_labels.values())
    for example in Node._examples:
        for node in example["workflow_snippet"]["nodes"]:
            if node["type"] == "OverseasFuturesHistoricalDataNode":
                assert node["interval"] in schema["interval"].enum_values
                assert node.get("adjust", False) is False

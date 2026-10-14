"""Preserve the published request fields through real SDK serialization, offline."""

import ast
import json
from pathlib import Path
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import requests

from programgarden_finance import CIDBQ02400
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.models import SetupOptions


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Request contract tests must remain offline")

    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    yield
    assert not attempts


def example_inputs():
    # Parse literals only: importing the example would load environment variables.
    path = Path(__file__).parents[1] / "example/overseas_futureoption/run_CIDBQ02400.py"
    calls = [node for node in ast.walk(ast.parse(path.read_text()))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == "CIDBQ02400InBlock1"]
    assert len(calls) == 1 and not calls[0].args
    assert all(keyword.arg is not None for keyword in calls[0].keywords)
    return {keyword.arg: ast.literal_eval(keyword.value) for keyword in calls[0].keywords}


def make_request(values):
    request = CIDBQ02400.CIDBQ02400Request(
        body={"CIDBQ02400InBlock1": CIDBQ02400.CIDBQ02400InBlock1(**values)},
        options=SetupOptions(rate_limit_key=""),
    )
    return CIDBQ02400.TrCIDBQ02400(request)


def response_payload():
    return {
        "rsp_cd": "00136", "rsp_msg": "Offline fixture",
        "CIDBQ02400OutBlock1": {"RecCnt": 7},
        "CIDBQ02400OutBlock2": [{
            "FutsOrdStatCode": "4", "ExecQty": 1,
            "CsgnCmsn": 1.25, "FcmCmsn": 0.125, "ThcoCmsn": 0.75,
        }],
    }


def assert_response_unchanged(result):
    assert not result.error_msg
    assert result.block1.RecCnt == 7
    assert result.block2[0].FutsOrdStatCode == "4"
    assert (result.block2[0].CsgnCmsn, result.block2[0].FcmCmsn,
            result.block2[0].ThcoCmsn) == (1.25, 0.125, 0.75)
    assert "block2" in result.model_fields_set


def test_current_official_request_fields_are_modeled_separately_from_response_echo():
    path = Path(__file__).parent / "fixtures/cidbq02400_official_request_fields.json"
    contract = json.loads(path.read_text())
    block, = contract["request"]
    assert block["element"] == "CIDBQ02400InBlock1"
    fields = {field["element"]: field for field in block["fields"]}
    assert len(fields) == 10
    assert fields["RecCnt"]["type"] == "Number" and fields["RecCnt"]["length"] == "5"
    assert set(fields) <= set(CIDBQ02400.CIDBQ02400InBlock1.model_fields)


def test_actual_example_values_survive_model_and_wire_serialization():
    values = example_inputs()
    assert values["RecCnt"] == 1
    tr = make_request(values)
    body = tr.request_data.body["CIDBQ02400InBlock1"]
    assert body.model_dump() == values
    assert tr._generic._build_json_body(tr.request_data) == {"CIDBQ02400InBlock1": values}


def test_existing_callers_can_omit_count_and_use_example_derived_sdk_default():
    values = example_inputs()
    values.pop("RecCnt")
    tr = make_request(values)
    body = tr.request_data.body["CIDBQ02400InBlock1"]
    assert "RecCnt" not in body.model_fields_set
    assert tr._generic._build_json_body(tr.request_data) == {
        "CIDBQ02400InBlock1": {"RecCnt": 1, **values},
    }


def test_explicit_count_is_not_overwritten_by_sdk_default():
    # Synthetic serialization value, not a broker-accepted range assertion.
    values = {**example_inputs(), "RecCnt": 2}
    tr = make_request(values)
    assert tr._generic._build_json_body(tr.request_data) == {"CIDBQ02400InBlock1": values}


def test_sync_transport_sends_complete_example_and_preserves_response(monkeypatch):
    wire = Mock(spec=requests.Response, status_code=200, headers={})
    wire.json.return_value = response_payload()
    post = Mock(return_value=wire)
    monkeypatch.setattr(requests, "post", post)
    values = example_inputs()
    result = make_request(values).req()
    assert post.call_count == 1
    assert post.call_args.kwargs["url"] == URLS.FO_ACCNO_URL
    assert post.call_args.kwargs["headers"]["tr_cd"] == "CIDBQ02400"
    assert post.call_args.kwargs["json"] == {"CIDBQ02400InBlock1": values}
    assert_response_unchanged(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("reuse_session", [False, True])
async def test_async_transport_sends_complete_example_and_preserves_response(monkeypatch, reuse_session):
    wire = MagicMock(status=200, headers={})
    wire.json = AsyncMock(return_value=response_payload())
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=wire)
    session = MagicMock()
    session.post.return_value = context
    session.__aenter__ = AsyncMock(return_value=session)
    monkeypatch.setattr("aiohttp.ClientSession", Mock(return_value=session))
    values = example_inputs()
    tr = make_request(values)
    result = await tr._req_async_with_session(session) if reuse_session else await tr.req_async()
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["url"] == URLS.FO_ACCNO_URL
    assert session.post.call_args.kwargs["headers"]["tr_cd"] == "CIDBQ02400"
    assert session.post.call_args.kwargs["json"] == {"CIDBQ02400InBlock1": values}
    assert_response_unchanged(result)


@pytest.mark.parametrize("echo", [{}, {"RecCnt": 0}, {"RecCnt": 7}])
def test_response_echo_retains_legacy_default_and_observed_presence(echo):
    result = CIDBQ02400.TrCIDBQ02400._build_response(
        None, SimpleNamespace(status_code=200),
        {"CIDBQ02400OutBlock1": echo, "CIDBQ02400OutBlock2": []}, {}, None,
    )
    assert not result.error_msg
    assert result.block1.RecCnt == echo.get("RecCnt", 0)
    assert ("RecCnt" in result.block1.model_fields_set) == ("RecCnt" in echo)
    assert result.block2 == [] and "block2" in result.model_fields_set

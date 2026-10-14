"""Unverified broker answers carry the broker's own message, bounded and log-safe.

The format matches the dsl-api startup gate:
``<TR>: unverified_response_code=<code> rsp_msg=<message>``. The prefix up to
the code is unchanged, so readers keyed on the old text still match. Responses
are real SDK models built from synthetic envelopes; no network access is made.
"""

import json
import re
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from requests import Response

from programgarden.database.broker_evidence import (
    StartupEvidenceUnavailable, broker_message, checked_body, unverified_response_code,
)
from programgarden.database.broker_snapshot import read_broker_snapshot
from programgarden.executor import OpenOrdersNodeExecutor
from programgarden_finance import CIDBQ01500, CIDBQ02400


EMPTY = "조회내역이 없습니다."
NEEDS_START_DATE = "조회시작일자를 입력 하십시오."
OLD_PREFIX = re.compile(r"^(?P<tr>[A-Za-z0-9]+): unverified_response_code=(?P<code>[0-9A-Za-z]*)")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    original = socket.socket.connect

    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Broker/network access is forbidden")
        return original(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr("programgarden.database.broker_snapshot.asyncio.sleep", AsyncMock())


def sdk_response(tr, request, *, code, message, echo=None):
    module = {"CIDBQ01500": CIDBQ01500, "CIDBQ02400": CIDBQ02400}[tr]
    body = {tr + "OutBlock1": {**request.model_dump(), "AcntNo": "offline-account", **(echo or {})},
            tr + "OutBlock2": [], "rsp_cd": code, "rsp_msg": message}
    headers = {"Content-Type": "application/json", "tr_cd": "CIDBQ", "tr_cont": "N", "tr_cont_key": ""}
    raw = Response()
    raw.status_code = 200
    raw._content = json.dumps(body).encode()
    return getattr(module, "Tr" + tr)._build_response(None, raw, body, headers, None)


def client(*, paper, position=("02679", EMPTY), orders=("02679", EMPTY)):
    calls = []

    def positions(*, body):
        calls.append("CIDBQ01500")
        result = sdk_response("CIDBQ01500", body, code=position[0], message=position[1],
                              echo={"QryDt": "20261014"})
        return NS(request_data=NS(body={"input": body}), req_async=AsyncMock(return_value=result))

    def pending(*, body):
        calls.append("CIDBQ02400")
        result = sdk_response("CIDBQ02400", body, code=orders[0], message=orders[1])
        return NS(request_data=NS(body={"input": body}), req_async=AsyncMock(return_value=result))

    accno = NS(CIDBQ01500=positions, CIDBQ02400=pending)
    manager = NS(appkey="offline-key", paper_trading=paper)
    return NS(token_manager=manager, overseas_futureoption=lambda: NS(accno=lambda: accno)), calls


@pytest.mark.asyncio
async def test_live_startup_rejection_names_the_broker_message():
    api, calls = client(paper=False)
    with pytest.raises(StartupEvidenceUnavailable) as error:
        await read_broker_snapshot(api, execution_key="offline-execution", product="overseas_futures",
                                   provider="ls", trading_mode="live")
    assert str(error.value) == f"CIDBQ01500: unverified_response_code=02679 rsp_msg={EMPTY}"
    assert calls == ["CIDBQ01500"]


@pytest.mark.asyncio
async def test_paper_pending_rejection_names_the_broker_message():
    api, calls = client(paper=True, orders=("03139", NEEDS_START_DATE))
    result = await OpenOrdersNodeExecutor()._ls_overseas_futures(api, "pending", NS(log=lambda *a, **k: None))
    assert result["error"] == f"CIDBQ02400: unverified_response_code=03139 rsp_msg={NEEDS_START_DATE}"
    assert result["open_orders"] == [] and calls == ["CIDBQ01500", "CIDBQ02400"]


@pytest.mark.asyncio
async def test_paper_empty_answers_are_still_accepted_without_an_error():
    api, calls = client(paper=True)
    result = await OpenOrdersNodeExecutor()._ls_overseas_futures(api, "pending", NS(log=lambda *a, **k: None))
    assert result == {"open_orders": [], "count": 0}
    assert calls == ["CIDBQ01500", "CIDBQ02400"]


@pytest.mark.asyncio
async def test_checked_body_message_keeps_the_previous_prefix():
    request = CIDBQ01500.CIDBQ01500InBlock1(RecCnt=1, AcntTpCode="1", FcmAcntNo="", QryDt="", BalTpCode="2")
    query = NS(request_data=NS(body={"input": request}))
    response = sdk_response("CIDBQ01500", request, code="02679", message=EMPTY)
    with pytest.raises(StartupEvidenceUnavailable) as error:
        await checked_body(response, "CIDBQ01500", query)
    match = OLD_PREFIX.match(str(error.value))
    assert match and match["tr"] == "CIDBQ01500" and match["code"] == "02679"
    assert str(error.value).startswith("CIDBQ01500: unverified_response_code=02679 rsp_msg=")


@pytest.mark.parametrize("message", [
    EMPTY, NEEDS_START_DATE, "모의투자 조회할 내역(자료)이 없습니다.", "", None, "x" * 120,
])
def test_ordinary_messages_match_the_server_gate_format(message):
    # dsl-api: f"{tr}: unverified_response_code={code} rsp_msg={str(response.rsp_msg or '')[:80]}"
    server = f"CIDBQ01500: unverified_response_code=02679 rsp_msg={str(message or '')[:80]}"
    assert unverified_response_code("CIDBQ01500", "02679", message) == server


@pytest.mark.parametrize("message,expected", [
    ("line one\nline two", "line one line two"),
    ("\r\n  padded\t", "padded"),
    ("nul\x00bell\x07", "nul bell"),
    ("bidi‮override", "bidi override"),
    ("가" * 200, "가" * 80),
    (12345, "12345"),
])
def test_broker_message_is_one_bounded_line(message, expected):
    text = broker_message(message)
    assert text == expected
    assert "\n" not in text and "\r" not in text and len(text) <= 80

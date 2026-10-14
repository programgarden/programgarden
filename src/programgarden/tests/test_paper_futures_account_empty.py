"""Paper 02679 empty-account answers on the explicit-date AccountNode read.

The SDK response models parse synthetic envelopes shaped like the 2026-10-14
paper observation (rsp_cd 02679, exact empty message, explicit empty detail
rows, terminal continuation). No network access is made.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from programgarden.executor import AccountNodeExecutor
from programgarden.futures_read_evidence import require_complete_rows

from futures_response_fixtures import parsed_response, position_request


EMPTY = "조회내역이 없습니다."
PAPER_EMPTY = "모의투자 조회할 내역(자료)이 없습니다."


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    original = socket.socket.connect

    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Broker/network access is forbidden")
        return original(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)


def paper_empty(request, **changes):
    options = {"code": "02679", "message": EMPTY}
    options.update(changes)
    return parsed_response("CIDBQ01500", request, options.pop("rows", []), **options)


@pytest.mark.parametrize("message", [EMPTY, PAPER_EMPTY])
def test_paper_02679_with_exact_empty_envelope_is_a_complete_empty_account(message):
    # Either exact wording the server startup gate accepts on this branch.
    request = position_request()
    response = paper_empty(request, message=message)
    assert require_complete_rows(response, request, "CIDBQ01500", paper_trading=True) == []


@pytest.mark.parametrize("message", [EMPTY, PAPER_EMPTY])
def test_live_02679_remains_unverified_and_names_the_broker_message(message):
    request = position_request()
    with pytest.raises(ValueError) as error:
        require_complete_rows(paper_empty(request, message=message), request, "CIDBQ01500")
    assert str(error.value) == f"CIDBQ01500: unverified_response_code=02679 rsp_msg={message}"


@pytest.mark.parametrize("case", [
    "truthy_non_bool_mode", "other_message", "rows_present", "missing_rows",
    "continuation", "wrong_echo", "other_tr",
])
def test_paper_02679_never_relaxes_other_completeness_guards(case):
    request = position_request()
    tr, paper, changes = "CIDBQ01500", True, {}
    if case == "truthy_non_bool_mode":
        paper = MagicMock()  # Only an explicit True paper mode qualifies.
    elif case == "other_message":
        changes["message"] = "조회시작일자를 입력 하십시오."
    elif case == "rows_present":
        changes["rows"] = [{"IsuCodeVal": "HMHU26", "BnsTpCode": "2", "BalQty": 1}]
    elif case == "missing_rows":
        changes["missing_rows"] = True
    elif case == "continuation":
        changes["continuation"] = True
    response = paper_empty(request, **changes)
    if case == "wrong_echo":
        response.block1.QryDt = "20000101"
    if case == "other_tr":
        tr = "CIDBQ05300"  # The relaxation is limited to the two observed TRs.
    with pytest.raises(ValueError):
        require_complete_rows(response, request, tr, paper_trading=paper)


def account_api(*, paper, position_code="02679", position_message=EMPTY, missing_rows=False):
    api = MagicMock()
    api.token_manager = SimpleNamespace(appkey="offline-key", paper_trading=paper)
    calls = []

    def positions_call(**kwargs):
        calls.append(kwargs["body"])
        result = parsed_response("CIDBQ01500", kwargs["body"], [], code=position_code,
                                 message=position_message, missing_rows=missing_rows)
        return SimpleNamespace(req_async=AsyncMock(return_value=result))

    def balance_call(**kwargs):
        result = parsed_response("CIDBQ05300", kwargs["body"], [
            {"CrcyCode": "USD", "AbrdFutsOrdAbleAmt": 1000, "OvrsFutsDps": 1000},
        ])
        return SimpleNamespace(req_async=AsyncMock(return_value=result))

    accno = api.overseas_futureoption.return_value.accno.return_value
    accno.CIDBQ01500.side_effect = positions_call
    accno.CIDBQ05300.side_effect = balance_call
    return api, calls


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [EMPTY, PAPER_EMPTY])
async def test_paper_account_node_reports_an_empty_account_instead_of_an_error(message):
    api, calls = account_api(paper=True, position_message=message)
    result = await AccountNodeExecutor()._ls_overseas_futureoption(api, "account", MagicMock())
    assert "error" not in result
    assert result["positions"] == [] and result["held_symbols"] == []
    assert not result["balance"].get("_partial_failure")
    assert result["balance"]["orderable_amount"] == 1000.0
    # The explicit-date request is unchanged; only the answer is recognized.
    assert len(calls) == 1 and calls[0].QryDt == position_request().QryDt


@pytest.mark.asyncio
async def test_live_account_node_keeps_rejecting_02679_with_the_broker_message():
    api, _ = account_api(paper=False)
    result = await AccountNodeExecutor()._ls_overseas_futureoption(api, "account", MagicMock())
    assert result["error"] == f"CIDBQ01500: unverified_response_code=02679 rsp_msg={EMPTY}"
    assert result["balance"]["_partial_failure"] is True


@pytest.mark.asyncio
async def test_paper_account_node_reports_a_rejection_message_verbatim():
    # A rejection without detail rows still surfaces the broker's own reason.
    api, _ = account_api(paper=True, position_code="03139", position_message="조회시작일자를 입력 하십시오.",
                         missing_rows=True)
    result = await AccountNodeExecutor()._ls_overseas_futureoption(api, "account", MagicMock())
    assert result["error"] == "CIDBQ01500: unverified_response_code=03139 rsp_msg=조회시작일자를 입력 하십시오."
    assert result["positions"] == []

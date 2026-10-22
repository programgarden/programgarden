"""Actual SDK parsing and executor checks for futures empty/failed reads."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from programgarden.executor import (
    AccountNodeExecutor,
    OpenOrdersNodeExecutor,
    MarketDataNodeExecutor,
)
from programgarden.futures_read_evidence import (
    require_complete_rows,
    require_pending_identity,
)
from programgarden_finance import CIDBQ01500, CIDBQ02400, CIDBQ05300, o3105


from futures_response_fixtures import parsed_response, position_request


@pytest.mark.parametrize(
    "case",
    ["missing_rows", "error", "wrong_echo", "partial", "wrong_header", "http_failure"],
)
def test_incomplete_position_response_is_never_an_empty_account(case):
    request = position_request()
    response = parsed_response(
        "CIDBQ01500",
        request,
        [],
        code="00707",
        missing_rows=case == "missing_rows",
        continuation=case == "partial",
    )
    if case == "error":
        response.rsp_cd = "REJECTED"
    if case == "wrong_echo":
        response.block1.QryDt = "20000101"
    if case == "wrong_header":
        response.header.tr_cd = "OTHER"
    if case == "http_failure":
        response.status_code = 503
    with pytest.raises(ValueError):
        require_complete_rows(response, request, "CIDBQ01500")


def test_observed_no_positions_response_is_normal():
    request = position_request()
    response = parsed_response("CIDBQ01500", request, [], code="00707")
    assert require_complete_rows(response, request, "CIDBQ01500") == []


@pytest.mark.parametrize(
    "missing", ["OvrsFutsOrdNo", "IsuCodeVal", "BnsTpCode", "UnercQty"]
)
def test_defaulted_pending_fields_do_not_disable_duplicate_guard(missing):
    row = {
        "OvrsFutsOrdNo": "12",
        "IsuCodeVal": "HMHU26",
        "BnsTpCode": "2",
        "OrdQty": 1,
        "ExecQty": 0,
        "UnercQty": 1,
    }
    row.pop(missing)
    with pytest.raises(ValueError):
        require_pending_identity(CIDBQ02400.CIDBQ02400OutBlock2(**row))


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False])
async def test_account_executor_propagates_missing_position_evidence(valid):
    api = MagicMock()

    def positions_call(**kwargs):
        result = parsed_response(
            "CIDBQ01500", kwargs["body"], [], code="00707", missing_rows=not valid
        )
        return SimpleNamespace(req_async=AsyncMock(return_value=result))

    def balance_call(**kwargs):
        result = parsed_response(
            "CIDBQ05300",
            kwargs["body"],
            [{"CrcyCode": "HKD", "AbrdFutsOrdAbleAmt": 1000, "OvrsFutsDps": 1000}],
        )
        return SimpleNamespace(req_async=AsyncMock(return_value=result))

    api.overseas_futureoption.return_value.accno.return_value.CIDBQ01500.side_effect = (
        positions_call
    )
    api.overseas_futureoption.return_value.accno.return_value.CIDBQ05300.side_effect = (
        balance_call
    )
    result = await AccountNodeExecutor()._ls_overseas_futureoption(
        api, "account", MagicMock()
    )
    assert bool(result["balance"].get("_partial_failure")) is not valid
    assert result["held_symbols"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False])
async def test_pending_executor_uses_same_day_terminal_query(valid):
    api = MagicMock()

    def query(**kwargs):
        assert kwargs["body"].ThdayTpCode == "1"
        result = parsed_response(
            "CIDBQ02400", kwargs["body"], [], code="00707", missing_rows=not valid
        )
        return SimpleNamespace(req_async=AsyncMock(return_value=result))

    api.overseas_futureoption.return_value.accno.return_value.CIDBQ02400.side_effect = (
        query
    )
    result = await OpenOrdersNodeExecutor()._ls_overseas_futures(
        api, "pending", MagicMock()
    )
    assert bool(result.get("error")) is not valid
    assert result["open_orders"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tick,expected", [(None, None), (0, None), (float("nan"), None), (1, 1)]
)
async def test_market_emits_only_observed_positive_tick_size(tick, expected):
    fields = {"Symbol": "HMHU26", "TrdP": 24760}
    if tick is not None:
        fields["UntPrc"] = tick
    response = o3105.O3105Response(
        status_code=200,
        rsp_cd="00000",
        rsp_msg="Offline",
        block=o3105.O3105OutBlock(**fields),
    )
    api = MagicMock()
    api.overseas_futureoption.return_value.market.return_value.o3105.return_value.req.return_value = response
    context = MagicMock()
    context.get_credential.return_value = {"appkey": "offline", "appsecret": "offline"}
    with patch(
        "programgarden.executor.ensure_ls_login", return_value=(api, True, None)
    ):
        result = await MarketDataNodeExecutor()._fetch_overseas_futures(
            [{"symbol": "HMHU26", "exchange": "HKEX"}], context, "market"
        )
    assert result["values"][0]["tick_size"] == expected


@pytest.mark.asyncio
async def test_market_does_not_label_another_contract_as_the_requested_one():
    response = o3105.O3105Response(
        status_code=200,
        rsp_cd="00000",
        rsp_msg="Offline",
        block=o3105.O3105OutBlock(Symbol="OTHER", TrdP=24760, UntPrc=1),
    )
    api = MagicMock()
    api.overseas_futureoption.return_value.market.return_value.o3105.return_value.req.return_value = response
    context = MagicMock()
    context.get_credential.return_value = {"appkey": "offline", "appsecret": "offline"}
    with patch(
        "programgarden.executor.ensure_ls_login", return_value=(api, True, None)
    ):
        result = await MarketDataNodeExecutor()._fetch_overseas_futures(
            [{"symbol": "HMHU26", "exchange": "HKEX"}], context, "market"
        )
    assert result["values"] == []

"""Paper current-day reads use observed broker dates, never the machine clock."""
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from requests import Response

from programgarden.database.broker_snapshot import read_broker_snapshot
from programgarden.executor import NewOrderNodeExecutor, OpenOrdersNodeExecutor
from programgarden_finance import CIDBQ01500, CIDBQ02400


DAY = "20260909"  # An overnight session may precede the machine's date.
ACCOUNT = "offline-account-a"


def response(tr, request, rows, *, change=None):
    module = {"CIDBQ01500": CIDBQ01500, "CIDBQ02400": CIDBQ02400}[tr]
    echo = {**request.model_dump(), "AcntNo": ACCOUNT}
    if tr == "CIDBQ01500":
        echo["QryDt"] = DAY
    body = {tr + "OutBlock1": echo, tr + "OutBlock2": rows,
            "rsp_cd": "00136" if rows else "02679",
            "rsp_msg": "Offline success" if rows else "조회내역이 없습니다."}
    headers = {"Content-Type": "application/json", "tr_cd": "CIDBQ", "tr_cont": "N", "tr_cont_key": ""}
    if change:
        change(body, headers)
    raw = Response()
    raw.status_code = 200
    raw._content = json.dumps(body).encode()
    return getattr(module, "Tr" + tr)._build_response(None, raw, body, headers, None)


def client(*, rows=None, position_change=None, order_change=None, after_positions=None, after_orders=None):
    calls = []
    manager = NS(appkey="offline-key-a", paper_trading=True)

    def positions(*, body):
        calls.append(("CIDBQ01500", body))
        result = response("CIDBQ01500", body, [], change=position_change)

        async def send():
            if after_positions:
                after_positions(manager)
            return result
        return NS(request_data=NS(body={"input": body}), req_async=send)

    def orders(*, body):
        calls.append(("CIDBQ02400", body))
        result = response("CIDBQ02400", body, rows or [], change=order_change)
        async def send():
            if after_orders:
                after_orders(manager)
            return result
        return NS(request_data=NS(body={"input": body}), req_async=send)

    accno = NS(CIDBQ01500=positions, CIDBQ02400=orders)
    return NS(token_manager=manager, overseas_futureoption=lambda: NS(accno=lambda: accno)), calls


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


async def invoke(path, api):
    context = NS(log=lambda *args, **kwargs: None)
    if path == "startup":
        return await read_broker_snapshot(api, execution_key="offline-execution",
            product="overseas_futures", provider="ls", trading_mode="paper")
    if path == "pending":
        return await OpenOrdersNodeExecutor()._ls_overseas_futures(api, "pending", context)
    return await NewOrderNodeExecutor()._query_overseas_futures_fill(api, "42", context, "order")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["startup", "pending", "fill"])
async def test_current_paper_query_uses_fresh_broker_day_and_complete_empty_evidence(path):
    api, calls = client()
    result = await invoke(path, api)
    assert [name for name, _ in calls] == ["CIDBQ01500", "CIDBQ02400"]
    first, second = [body for _, body in calls]
    assert (first.RecCnt, first.AcntTpCode, first.QryDt, first.BalTpCode, first.FcmAcntNo) == (1, "1", "", "2", "")
    assert second.QrySrtDt == second.QryEndDt == DAY
    assert second.ThdayTpCode == "1"
    assert second.OrdStatCode == ("0" if path == "fill" else "2")
    assert second.QryTpCode == ("1" if path == "fill" else "2")
    if path == "startup":
        assert result.pending_orders == () and result.positions.quantities == {}
    elif path == "pending":
        assert result == {"open_orders": [], "count": 0}
    else:
        assert result == (0, 0.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", ["date_missing", "date_blank", "date_invalid", "account_missing",
                                      "filter_mismatch", "missing_rows", "continuation", "rejected"])
async def test_missing_or_invalid_date_evidence_does_not_query_pending_orders(defect):
    def mutate(body, headers):
        echo = body["CIDBQ01500OutBlock1"]
        if defect == "date_missing": echo.pop("QryDt")
        elif defect == "date_blank": echo["QryDt"] = ""
        elif defect == "date_invalid": echo["QryDt"] = "20260230"
        elif defect == "account_missing": echo.pop("AcntNo")
        elif defect == "filter_mismatch": echo["BalTpCode"] = "1"
        elif defect == "missing_rows": body.pop("CIDBQ01500OutBlock2")
        elif defect == "continuation": headers.update(tr_cont="Y", tr_cont_key="next")
        elif defect == "rejected": body["rsp_cd"] = "03139"
    api, calls = client(position_change=mutate)
    result = await invoke("pending", api)
    assert result.get("error")
    assert [name for name, _ in calls] == ["CIDBQ01500"]


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("appkey", "offline-key-b"), ("paper_trading", False)])
async def test_credential_or_mode_switch_discards_date_without_retry(field, value):
    api, calls = client(after_positions=lambda manager: setattr(manager, field, value))
    result = await invoke("pending", api)
    assert result.get("error")
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", ["account", "date", "filter", "missing_filter", "missing_rows",
                                      "rejected", "message", "continuation", "cursor"])
async def test_pending_read_never_treats_incomplete_or_cross_account_evidence_as_empty(defect):
    def mutate(body, headers):
        echo = body["CIDBQ02400OutBlock1"]
        if defect == "account": echo["AcntNo"] = "offline-account-b"
        elif defect == "date": echo["QryEndDt"] = "20260910"
        elif defect == "filter": echo["BnsTpCode"] = "1"
        elif defect == "missing_filter": echo.pop("BnsTpCode")
        elif defect == "missing_rows": body.pop("CIDBQ02400OutBlock2")
        elif defect == "rejected": body["rsp_cd"] = "03139"
        elif defect == "message": body["rsp_msg"] = "Unknown no-data message"
        elif defect == "continuation": headers.update(tr_cont="Y", tr_cont_key="next")
        elif defect == "cursor": headers["tr_cont_key"] = "next"
    api, calls = client(order_change=mutate)
    result = await invoke("pending", api)
    assert result.get("error")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_paper_partial_fills_match_order_without_local_day_substitution():
    rows = [{"IsuCodeVal": "CONTRACT", "OvrsFutsOrdNo": number, "OrdDt": DAY,
             "UnercQty": 0, "ExecQty": quantity, "AbrdFutsExecPrc": price}
            for number, quantity, price in [("42", 1, 100), ("other", 9, 1), ("42", 2, 103)]]
    api, calls = client(rows=rows)
    assert await invoke("fill", api) == (3, 102.0)
    assert calls[1][1].QrySrtDt == DAY


@pytest.mark.asyncio
async def test_startup_rejection_never_authorizes_empty_positions_or_orders():
    api, calls = client(order_change=lambda body, headers: body.pop("CIDBQ02400OutBlock2"))
    with pytest.raises(RuntimeError):
        await invoke("startup", api)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_expired_date_evidence_is_not_replaced_with_local_today(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("programgarden.paper_futures_business_date.time.monotonic", lambda: clock[0])
    api, calls = client(after_positions=lambda manager: clock.__setitem__(0, 161.0))
    result = await invoke("pending", api)
    assert "expired_observation" in result["error"]
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("appkey", "offline-key-b"), ("paper_trading", False)])
async def test_scope_switch_during_order_read_never_confirms_empty(field, value):
    api, calls = client(after_orders=lambda manager: setattr(manager, field, value))
    result = await invoke("pending", api)
    assert result.get("error")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_generic_empty_code_is_not_globally_accepted_for_live_startup():
    from programgarden.database.broker_evidence import checked_body, StartupEvidenceUnavailable
    api, _ = client()
    body = CIDBQ01500.CIDBQ01500InBlock1(RecCnt=1, AcntTpCode="1", FcmAcntNo="", QryDt="", BalTpCode="2")
    query = api.overseas_futureoption().accno().CIDBQ01500(body=body)
    with pytest.raises(StartupEvidenceUnavailable, match="unverified_response_code=02679"):
        await checked_body(await query.req_async(), "CIDBQ01500", query)


def test_business_date_and_account_fields_exist_in_actual_sdk_models():
    assert {"QryDt", "AcntNo", "AcntTpCode", "BalTpCode", "FcmAcntNo"} <= CIDBQ01500.CIDBQ01500OutBlock1.model_fields.keys()
    assert {"AcntNo", "QrySrtDt", "QryEndDt", "ThdayTpCode", "OrdStatCode", "IsuCodeVal",
            "BnsTpCode", "QryTpCode", "OrdPtnCode", "OvrsDrvtFnoTpCode"} <= CIDBQ02400.CIDBQ02400OutBlock1.model_fields.keys()

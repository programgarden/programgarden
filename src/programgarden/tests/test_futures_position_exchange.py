"""Futures account and pending-order rows take their exchange from o3105.

CIDBQ01500 and CIDBQ02400 carry no exchange field. Before 2.6.5 the engine
labelled every futures position, held symbol and pending order "HKEX", so a
workflow comparing a CME position's exchange with "CME" never matched. The
exchange now comes from o3105 ``ExchCd`` under the contract-detail identity
rules, and stays ``None`` when that evidence is unavailable.

Broker answers are real SDK models: CIDBQ01500/CIDBQ05300/CIDBQ02400 bodies are
parsed by their SDK TR classes (``futures_response_fixtures``) and o3105 bodies
by ``TrO3105._build_response``. One case drives the actual ``LS`` client with
only the HTTP transport replaced. Values are synthetic.
"""

import asyncio
import socket
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from futures_response_fixtures import parsed_response
from programgarden import futures_exchange
from programgarden.context import ExecutionContext
from programgarden.executor import AccountNodeExecutor, OpenOrdersNodeExecutor
from programgarden_finance.ls.overseas_futureoption.market.o3105 import TrO3105
from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105InBlock


EXCHANGES = {"MNQZ26": "CME", "HMHV26": "HKEX"}


def o3105_response(symbol, exchange, *, code="00000", status=200, echo=None, include_exchange=True):
    block = {"Symbol": symbol if echo is None else echo, "SymbolNm": symbol, "ExchNm": "", "TrdP": 1.0}
    if include_exchange:
        block["ExchCd"] = exchange
    body = {"o3105OutBlock": block, "rsp_cd": code, "rsp_msg": "Offline fixture"}
    header = {"Content-Type": "application/json; charset=utf-8", "tr_cd": "o3105", "tr_cont": "N", "tr_cont_key": ""}
    return TrO3105._build_response(None, SimpleNamespace(status_code=status), body, header, None)


def position_row(symbol, *, side="2", qty=1, pos_no="1"):
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    return {
        "BaseDt": today, "Dps": 0, "LpnlAmt": 0, "FutsDueBfLpnlAmt": 0, "FutsDueBfCmsn": 0,
        "CsgnMgn": 0, "MaintMgn": 0, "CtlmtAmt": 0, "AddMgn": 0, "MgnclRat": 0,
        "OrdAbleAmt": 0, "WthdwAbleAmt": 0, "AcntNo": "offline", "IsuCodeVal": symbol,
        "IsuNm": symbol, "CrcyCodeVal": "USD", "OvrsDrvtPrdtCode": "", "OvrsDrvtOptTpCode": "",
        "DueDt": "", "OvrsDrvtXrcPrc": 0, "BnsTpCode": side, "CmnCodeNm": "", "TpCodeNm": "",
        "BalQty": qty, "PchsPrc": 25000.0, "OvrsDrvtNowPrc": 24900.0, "AbrdFutsEvalPnlAmt": -200.0,
        "CsgnCmsn": 0, "PosNo": pos_no, "EufOneCmsnAmt": 0, "EufTwoCmsnAmt": 0,
    }


def pending_row(symbol, order_no):
    return {
        "OvrsFutsOrdNo": order_no, "IsuCodeVal": symbol, "IsuNm": symbol, "BnsTpCode": "2",
        "OrdQty": 1, "ExecQty": 0, "UnercQty": 1, "OvrsDrvtOrdPrc": 24000.0,
        "OrdSndDttm": "20261015093000000",
    }


class Broker:
    """MagicMock LS client whose TR factories return SDK-parsed envelopes."""

    def __init__(self, positions=(), pending=(), o3105=None, events=None):
        self.events = [] if events is None else events
        self.o3105_bodies = []
        self._o3105 = o3105 or (lambda symbol: o3105_response(symbol, EXCHANGES.get(symbol, "")))
        api = MagicMock()
        futures = api.overseas_futureoption.return_value
        accno = futures.accno.return_value
        accno.CIDBQ01500.side_effect = lambda body: self._query(
            "CIDBQ01500", parsed_response("CIDBQ01500", body, list(positions),
                                          code="00000" if positions else "00707"))
        accno.CIDBQ05300.side_effect = lambda body: self._query(
            "CIDBQ05300", parsed_response("CIDBQ05300", body, [
                {"CrcyCode": "USD", "AbrdFutsOrdAbleAmt": 5000.0, "OvrsFutsDps": 5000.0}]))
        accno.CIDBQ02400.side_effect = lambda body: self._query(
            "CIDBQ02400", parsed_response("CIDBQ02400", body, list(pending),
                                          code="00000" if pending else "00707"))
        futures.market.return_value.o3105.side_effect = self._o3105_query
        self.api = api

    def _query(self, tr, response):
        async def req_async():
            self.events.append(tr)
            return response
        return SimpleNamespace(req_async=req_async)

    def _o3105_query(self, body):
        assert isinstance(body, O3105InBlock)
        self.o3105_bodies.append(body)

        async def req_async():
            self.events.append(("o3105", body.symbol))
            result = self._o3105(body.symbol)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        return SimpleNamespace(req_async=req_async)

    @property
    def o3105_symbols(self):
        return [body.symbol for body in self.o3105_bodies]


class Context:
    def __init__(self):
        self.logs = []

    def log(self, level, message, node_id=None, **_):
        self.logs.append((level, message))


async def account(broker, context):
    return await AccountNodeExecutor()._ls_overseas_futureoption(broker.api, "account", context)


async def pending(broker, context):
    return await OpenOrdersNodeExecutor()._ls_overseas_futures(broker.api, "pending", context)


@pytest.mark.asyncio
async def test_positions_and_held_symbols_take_the_o3105_exchange():
    broker = Broker(positions=[position_row("MNQZ26"), position_row("HMHV26", side="1", pos_no="2")])
    result = await account(broker, Context())

    assert [(p["symbol"], p["exchange"]) for p in result["positions"]] == [("MNQZ26", "CME"), ("HMHV26", "HKEX")]
    assert result["held_symbols"] == [{"exchange": "CME", "symbol": "MNQZ26"}, {"exchange": "HKEX", "symbol": "HMHV26"}]
    # Request fields follow the SDK example (symbol only); positions and balance are read first.
    assert [body.model_dump() for body in broker.o3105_bodies] == [{"symbol": "MNQZ26"}, {"symbol": "HMHV26"}]
    assert broker.events == ["CIDBQ01500", "CIDBQ05300", ("o3105", "MNQZ26"), ("o3105", "HMHV26")]
    # The beginner guide's identity check (symbol and exchange both equal) now matches a CME position.
    instrument = {"symbol": "MNQZ26", "exchange": "CME"}
    relevant = [p for p in result["positions"] if p["symbol"] == instrument["symbol"]]
    assert len(relevant) == 1 and relevant[0]["exchange"] == instrument["exchange"]
    assert not result["balance"].get("_partial_failure")


def _unavailable(case):
    if case == "blank_exchange":
        return lambda symbol: o3105_response(symbol, "   ")
    if case == "missing_exchange_field":
        return lambda symbol: o3105_response(symbol, "CME", include_exchange=False)
    if case == "other_symbol":
        return lambda symbol: o3105_response(symbol, "CME", echo="MNQH27")
    if case == "broker_error_code":
        return lambda symbol: o3105_response(symbol, "CME", code="IGW00121")
    if case == "http_error":
        return lambda symbol: o3105_response(symbol, "CME", status=500)
    if case == "transport_exception":
        def fail(symbol):
            raise ConnectionError("offline")
        return fail
    raise AssertionError(case)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [
    "blank_exchange", "missing_exchange_field", "other_symbol",
    "broker_error_code", "http_error", "transport_exception",
])
async def test_unresolved_exchange_is_none_never_a_default(case):
    broker = Broker(positions=[position_row("MNQZ26")], o3105=_unavailable(case))
    context = Context()
    result = await account(broker, context)

    assert result["positions"][0]["exchange"] is None
    assert result["held_symbols"] == [{"exchange": None, "symbol": "MNQZ26"}]
    assert "HKEX" not in repr(result) and "CME" not in repr(result)
    # The position itself and the balance stay available; only the exchange is unknown.
    assert result["positions"][0]["quantity"] == 1 and not result["balance"].get("_partial_failure")
    assert any(level == "warning" and "MNQZ26" in message for level, message in context.logs)
    assert broker.o3105_symbols == ["MNQZ26"]


@pytest.mark.asyncio
async def test_timed_out_read_is_unresolved(monkeypatch):
    monkeypatch.setattr(futures_exchange, "READ_TIMEOUT_SECONDS", 0.01)

    async def never(symbol):
        await asyncio.sleep(5)

    broker = Broker(positions=[position_row("MNQZ26")], o3105=never)
    started = time.monotonic()
    result = await account(broker, Context())
    assert time.monotonic() - started < 2
    assert result["positions"][0]["exchange"] is None


@pytest.mark.asyncio
async def test_one_o3105_per_symbol_per_run_including_unresolved_answers():
    answers = {"MNQZ26": "CME", "HMHV26": ""}
    broker = Broker(
        positions=[position_row("MNQZ26"), position_row("MNQZ26", pos_no="2"), position_row("HMHV26", pos_no="3")],
        pending=[pending_row("MNQZ26", "1001"), pending_row("HMHV26", "1002")],
        o3105=lambda symbol: o3105_response(symbol, answers[symbol]),
    )
    context = Context()
    first = await account(broker, context)
    answers.update({"HMHV26": "HKEX"})  # a later answer must not be requested again in this run
    second = await account(broker, context)
    orders = await pending(broker, context)

    assert broker.o3105_symbols == ["MNQZ26", "HMHV26"]
    for result in (first, second):
        assert [p["exchange"] for p in result["positions"]] == ["CME", "CME", None]
    assert [(o["symbol"], o["exchange"]) for o in orders["open_orders"]] == [("MNQZ26", "CME"), ("HMHV26", None)]

    # A new run asks again.
    await account(broker, Context())
    assert broker.o3105_symbols == ["MNQZ26", "HMHV26", "MNQZ26", "HMHV26"]


@pytest.mark.asyncio
async def test_concurrent_nodes_in_one_run_share_a_single_read():
    async def slow(symbol):
        await asyncio.sleep(0.01)
        return o3105_response(symbol, EXCHANGES[symbol])

    broker = Broker(positions=[position_row("MNQZ26")], pending=[pending_row("MNQZ26", "1001")], o3105=slow)
    context = Context()
    results = await asyncio.gather(account(broker, context), account(broker, context), pending(broker, context))

    assert broker.o3105_symbols == ["MNQZ26"]
    assert results[0]["positions"][0]["exchange"] == results[1]["positions"][0]["exchange"] == "CME"
    assert results[2]["open_orders"][0]["exchange"] == "CME"


@pytest.mark.asyncio
async def test_reads_are_spaced_like_startup_reads_and_only_when_reading(monkeypatch):
    events = []

    async def record_sleep(seconds):
        events.append(("sleep", seconds))

    monkeypatch.setattr(futures_exchange, "READ_SPACING_SECONDS", 2.0)
    monkeypatch.setattr(futures_exchange, "_sleep", record_sleep)
    broker = Broker(positions=[position_row("MNQZ26"), position_row("HMHV26", pos_no="2")], events=events)
    context = Context()
    await account(broker, context)
    assert events == [
        "CIDBQ01500", "CIDBQ05300",
        ("sleep", 2.0), ("o3105", "MNQZ26"),
        ("sleep", 2.0), ("o3105", "HMHV26"),
    ]

    events.clear()
    await account(broker, context)
    assert events == ["CIDBQ01500", "CIDBQ05300"]


@pytest.mark.asyncio
async def test_empty_account_and_empty_pending_make_no_o3105_read(monkeypatch):
    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(futures_exchange, "_sleep", record_sleep)
    broker = Broker()
    context = Context()
    result = await account(broker, context)
    orders = await pending(broker, context)
    assert result["positions"] == [] and result["held_symbols"] == []
    assert orders["open_orders"] == []
    assert broker.o3105_symbols == [] and sleeps == []


@pytest.mark.asyncio
async def test_pending_orders_take_the_o3105_exchange():
    broker = Broker(pending=[pending_row("MNQZ26", "1001"), pending_row("HMHV26", "1002")])
    orders = await pending(broker, Context())
    assert [(o["order_id"], o["symbol"], o["exchange"]) for o in orders["open_orders"]] == [
        ("1001", "MNQZ26", "CME"), ("1002", "HMHV26", "HKEX"),
    ]
    assert broker.events == ["CIDBQ02400", ("o3105", "MNQZ26"), ("o3105", "HMHV26")]


@pytest.mark.asyncio
async def test_unresolved_pending_order_exchange_is_none():
    broker = Broker(pending=[pending_row("MNQZ26", "1001")], o3105=_unavailable("blank_exchange"))
    orders = await pending(broker, Context())
    assert orders["open_orders"][0]["exchange"] is None and "error" not in orders


@pytest.mark.asyncio
async def test_execution_context_keeps_the_run_cache():
    broker = Broker(positions=[position_row("MNQZ26")])
    context = ExecutionContext(job_id="job-exchange", workflow_id="wf-exchange")
    assert context._futures_exchange_cache is None
    await account(broker, context)
    await account(broker, context)
    assert broker.o3105_symbols == ["MNQZ26"]
    assert context._futures_exchange_cache.exchanges == {"MNQZ26": "CME"}


@pytest.mark.parametrize("block,expected", [
    ({"Symbol": "MNQZ26  ", "ExchCd": " CME "}, "CME"),
    ({"Symbol": "MNQZ26", "ExchCd": ""}, None),
    ({"Symbol": "MNQZ26"}, None),
    ({"ExchCd": "CME"}, None),
    ({"Symbol": "mnqz26", "ExchCd": "CME"}, None),
])
def test_contract_detail_identity_rules(block, expected):
    body = {"o3105OutBlock": block, "rsp_cd": "00000", "rsp_msg": "Offline fixture"}
    header = {"Content-Type": "application/json", "tr_cd": "o3105", "tr_cont": "N", "tr_cont_key": ""}
    response = TrO3105._build_response(None, SimpleNamespace(status_code=200), body, header, None)
    assert futures_exchange.exchange_from_contract_detail(response, "MNQZ26") == expected


def test_missing_response_block_is_unresolved():
    response = TrO3105._build_response(None, SimpleNamespace(status_code=200), {"rsp_cd": "00000"}, {}, None)
    assert futures_exchange.exchange_from_contract_detail(response, "MNQZ26") is None
    failed = TrO3105._build_response(None, None, None, None, ConnectionError("offline"))
    assert futures_exchange.exchange_from_contract_detail(failed, "MNQZ26") is None


@pytest.mark.asyncio
async def test_actual_sdk_client_sends_the_example_o3105_request(monkeypatch):
    """Drive the real LS client and TR classes; only the HTTP transport is replaced."""
    from programgarden_finance import LS
    from programgarden_finance.ls import tr_helpers

    original_connect = socket.socket.connect

    def offline(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError(f"network blocked: {address!r}")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", offline)
    sent = []

    class Reply:
        status = status_code = 200

        def __init__(self, body, headers):
            self._body, self.headers = body, headers

        def json(self):
            return self._body

    async def transport(self, session, url, request_data, timeout=10):
        tr = request_data.header.tr_cd
        block = next(iter(request_data.body.values())).model_dump()
        sent.append((tr, block))
        if tr == "CIDBQ01500":
            body = {"CIDBQ01500OutBlock1": {**block, "AcntNo": "offline", "Pwd": ""},
                    "CIDBQ01500OutBlock2": [position_row("MNQZ26")], "rsp_cd": "00000", "rsp_msg": "Offline"}
        elif tr == "CIDBQ05300":
            body = {"CIDBQ05300OutBlock1": {**block, "AcntNo": "offline"},
                    "CIDBQ05300OutBlock2": [{"CrcyCode": "USD", "AbrdFutsOrdAbleAmt": 5000.0, "OvrsFutsDps": 5000.0}],
                    "CIDBQ05300OutBlock3": {}, "rsp_cd": "00000", "rsp_msg": "Offline"}
        elif tr == "o3105":
            body = {"o3105OutBlock": {"Symbol": block["symbol"], "ExchCd": "CME"}, "rsp_cd": "00000", "rsp_msg": "Offline"}
        else:
            raise AssertionError(tr)
        headers = {"Content-Type": "application/json; charset=utf-8", "tr_cd": tr, "tr_cont": "N", "tr_cont_key": ""}
        return Reply(body, headers), body, headers

    monkeypatch.setattr(tr_helpers.GenericTR, "execute_async_with_session", transport)

    ls = object.__new__(LS)
    ls.__init__()
    manager = ls.token_manager
    manager.appkey = "offline-appkey"
    manager.access_token = "offline-placeholder"
    manager.token_type = "Bearer"
    manager.expires_in = 86400
    manager.acquired_at = time.time()
    if hasattr(manager, "configure_trading_mode"):
        manager.configure_trading_mode(True)
    else:
        manager.paper_trading = True

    result = await AccountNodeExecutor()._ls_overseas_futureoption(ls, "account", Context())
    assert [tr for tr, _ in sent] == ["CIDBQ01500", "CIDBQ05300", "o3105"]
    assert sent[-1] == ("o3105", {"symbol": "MNQZ26"})
    assert result["positions"][0]["exchange"] == "CME"
    assert result["held_symbols"] == [{"exchange": "CME", "symbol": "MNQZ26"}]

"""Opt-in replay transport (finance 2.0.6), offline.

Default off: with no transport installed, ``tr_base`` sends exactly as before.
With a transport installed (a ContextVar), a TR is answered from it, never the
network; token issuance is refused; GenericTR neither retries nor reissues.
"""
import asyncio
import socket
import time
from types import SimpleNamespace

import pytest

from programgarden_finance.ls import replay_transport as rt
from programgarden_finance.ls import tr_helpers as trh
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("network access with a replay transport installed")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class Tape:
    def __init__(self, status=200, payload=None, headers=None):
        self.status, self.payload = status, payload if payload is not None else {"rsp_cd": "00000"}
        self.headers = headers or {"Content-Type": "application/json; charset=utf-8", "tr_cd": "g3203",
                                   "tr_cont": "N", "tr_cont_key": ""}
        self.calls, self.refusals = [], []

    def answer(self, tr_cd, url, header, body):
        self.calls.append({"tr": tr_cd, "url": url, "header": header, "body": body})
        return self.status, self.payload, self.headers

    def refused(self, kind, detail):
        self.refusals.append(kind)


def _g3203(client):
    from programgarden_finance.ls.overseas_stock.chart.g3203.blocks import G3203InBlock
    return client.overseas_stock().chart().g3203(body=G3203InBlock(
        keysymbol="82NVDA", exchcd="82", symbol="NVDA", ncnt=15, qrycnt=2, sdate="20261015", edate="20261016"))


BARS = {"rsp_cd": "00000", "rsp_msg": "synthetic", "g3203OutBlock1": [
    {"date": "20261016", "loctime": "093000", "open": 1.0, "high": 2.0, "low": 0.5, "close": "1.5000",
     "exevol": 10, "amount": 0},
    {"date": "20261016", "loctime": "094500", "open": 1.5, "high": 2.5, "low": 1.0, "close": "2.0000",
     "exevol": 11, "amount": 0}]}


def test_default_is_off():
    assert rt.active_transport() is None
    with pytest.raises(TypeError):
        with rt.use_replay_transport(object()):
            pass


@pytest.mark.asyncio
async def test_without_a_transport_the_request_goes_to_the_session_unchanged():
    from programgarden_finance.ls.tr_base import TRRequestAbstract

    class Probe(TRRequestAbstract):
        def req(self):  # pragma: no cover - abstract stubs
            raise NotImplementedError

        async def req_async(self):  # pragma: no cover
            raise NotImplementedError

    posted = []

    class Response:
        status = 200
        headers = {"tr_cd": "x"}

        async def json(self):
            return {"rsp_cd": "00000"}

        def raise_for_status(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class Session:
        def post(self, **kwargs):
            posted.append(kwargs)
            return Response()

    tr = Probe(rate_limit_count=10, rate_limit_seconds=1)
    request = SimpleNamespace(header=SimpleNamespace(model_dump=lambda by_alias: {"tr_cd": "x"}),
                              body={"xInBlock": {"a": 1}})
    resp, payload, headers = await tr.execute_async_with_session(Session(), "https://ls.invalid/x", request)
    assert posted == [{"url": "https://ls.invalid/x", "headers": {"tr_cd": "x"}, "json": {"xInBlock": {"a": 1}}}]
    assert payload == {"rsp_cd": "00000"} and headers == {"tr_cd": "x"}


@pytest.mark.asyncio
async def test_installed_transport_answers_async_and_sync_with_the_real_parser(no_network):
    tape = Tape(payload=BARS)
    with rt.use_replay_transport(tape):
        client = rt.replay_client(False)
        response = await _g3203(client).req_async()
        sync_response = _g3203(client).req()
    assert response.error_msg is None and sync_response.error_msg is None
    assert [row.close for row in response.block1] == ["1.5000", "2.0000"]
    assert response.header.tr_cd == "g3203"
    call = tape.calls[0]
    assert call["tr"] == "g3203" and call["url"].endswith("/overseas-stock/chart")
    assert "authorization" not in call["header"]          # a transport never sees a token
    assert call["body"]["g3203InBlock"]["keysymbol"] == "82NVDA" and call["body"]["g3203InBlock"]["ncnt"] == 15
    assert len(tape.calls) == 2
    assert rt.active_transport() is None


@pytest.mark.asyncio
async def test_a_refused_answer_becomes_an_error_response_without_retry(no_network):
    class Refusing(Tape):
        def answer(self, tr_cd, url, header, body):
            self.calls.append(tr_cd)
            raise rt.ReplayTransportRefused("no answer recorded")

    tape = Refusing()
    with rt.use_replay_transport(tape):
        response = await _g3203(rt.replay_client(False)).req_async()
    assert "no answer recorded" in (response.error_msg or "")
    assert tape.calls == ["g3203"]


@pytest.mark.asyncio
async def test_token_issuance_is_refused(no_network):
    from programgarden_finance.ls import LS
    tape = Tape()
    with rt.use_replay_transport(tape):
        client = object.__new__(LS)
        client.__init__()
        assert client.login(appkey="k", appsecretkey="s") is False
        assert await client.async_login(appkey="k", appsecretkey="s") is False
        assert not client.is_logged_in()
    assert tape.refusals == ["token", "token"]
    assert tape.calls == []


def _token_manager():
    issued = []

    def provider(*, force_reissue=False, stale_token=None):
        issued.append(force_reissue)
        return ("FRESH", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.apply_token("CURRENT", time.time() + 3600)
    return tm, issued


def _generic(url, token_manager):
    options = SetupOptions(rate_limit_count=100, rate_limit_seconds=1, on_rate_limit="wait", rate_limit_key="")
    options.token_manager = token_manager
    request_data = SimpleNamespace(options=options, header=SimpleNamespace(
        authorization="Bearer CURRENT", tr_cd="t0425", model_dump=lambda by_alias: {"tr_cd": "t0425"}),
        body={})
    return trh.GenericTR(request_data, lambda resp, rj, rh, exc: (resp, rj, rh, exc), url=url)


@pytest.mark.asyncio
@pytest.mark.parametrize("status,payload", [
    (500, {"rsp_cd": "IGW00121", "rsp_msg": "유효하지 않은 토큰입니다."}),   # token invalid
    (500, {"rsp_cd": "IGW00201", "rsp_msg": "호출 거래건수를 초과하였습니다."}),  # transient
])
async def test_generic_tr_never_retries_or_reissues_under_a_transport(monkeypatch, status, payload, no_network):
    async def no_sleep(_s):
        pytest.fail("slept for a retry under a replay transport")
    monkeypatch.setattr(trh.asyncio, "sleep", no_sleep)
    tm, issued = _token_manager()
    tape = Tape(status=status, payload=payload)
    gtr = _generic("https://ls.invalid/stock/accno", tm)
    with rt.use_replay_transport(tape):
        resp, rj, _rh = await gtr._execute_async_with_retry(None)
        sync_resp, _, _ = gtr._execute_sync_with_retry()
    assert resp.status == 500 and sync_resp.status == 500 and rj == payload
    assert len(tape.calls) == 2           # one async + one sync attempt, no retry
    assert issued == [] and tm.access_token == "CURRENT"
    if payload["rsp_cd"] == "IGW00121":
        assert tape.refusals == ["token_reissue", "token_reissue"]


@pytest.mark.asyncio
async def test_the_transport_is_visible_only_to_the_installing_task(no_network):
    seen = []

    async def other():
        for _ in range(5):
            seen.append(rt.active_transport())
            await asyncio.sleep(0)

    task = asyncio.create_task(other())
    with rt.use_replay_transport(Tape()):
        for _ in range(5):
            await asyncio.sleep(0)
        child = await asyncio.create_task(asyncio.sleep(0, result=rt.active_transport()))
    await task
    assert seen == [None] * 5
    assert child is not None  # a task created inside the block inherits it


def test_replay_client_is_fresh_and_logged_in_without_a_login():
    from programgarden_finance.ls import LS
    a, b = rt.replay_client(True), rt.replay_client(False)
    assert a is not b and a is not LS()
    assert a.is_logged_in() and a.token_manager.paper_trading is True
    assert a.token_manager.token_provider is None

"""Account-event registration across reconnects and futures unregister (SPEC K2/K3).

K2: after a reconnect the SDK re-sends market subscriptions and, by default,
the account (order event) registration of every family still in use. The
option ``reregister_account_events_on_reconnect=False`` keeps the old
behaviour. Verified against a local websocket server (no external network).

K3: when the last listener goes away, the overseas futures client sends one
account unregister (``tr_type="2"``) with the same body it registered with
(``tr_cd="TC1"``, ``tr_key=""``) and clears its flag.
"""

import asyncio
import json
import time

import pytest
from websockets.asyncio.server import serve

from programgarden_finance.ls.korea_stock.real import Real as KoreaReal
from programgarden_finance.ls.overseas_futureoption.real import Real as FuturesReal
from programgarden_finance.ls.overseas_stock.real import Real as StockReal
from programgarden_finance.ls.token_manager import TokenManager


def _token_manager(wss_url=None) -> TokenManager:
    tm = TokenManager()
    tm.access_token = "stub-access-token"
    tm.wss_url = wss_url
    return tm


class _FakeSocket:
    def __init__(self):
        self.frames = []

    async def send(self, raw):
        self.frames.append(json.loads(raw))


def _connected(real_cls):
    real = real_cls(token_manager=_token_manager())
    real._connected_event.set()
    real._ws = _FakeSocket()
    return real


async def _drain():
    for _ in range(5):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# K3 — futures unregister
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_futures_last_listener_sends_one_unregister_and_clears_flag():
    real = _connected(FuturesReal)
    listener = lambda resp: None  # noqa: E731
    real.TC1().on_tc1_message(listener)
    await _drain()
    real.TC1().on_remove_tc1_message(listener)
    await _drain()

    register, unregister = real._ws.frames
    assert register["header"] == {"token": "stub-access-token", "tr_type": "1"}
    assert register["body"] == {"tr_cd": "TC1", "tr_key": ""}
    assert unregister["header"] == {"token": "stub-access-token", "tr_type": "2"}
    assert unregister["body"] == {"tr_cd": "TC1", "tr_key": ""}
    assert real._tc123_connect is False


@pytest.mark.asyncio
async def test_futures_unregister_waits_for_the_last_listener_and_reregisters_later():
    real = _connected(FuturesReal)
    a, b = (lambda r: None), (lambda r: None)
    real.TC2().on_tc2_message(a)
    real.TC3().on_tc3_message(b)
    await _drain()
    real.TC2().on_remove_tc2_message(a)
    await _drain()
    assert [f["header"]["tr_type"] for f in real._ws.frames] == ["1"]
    real.TC3().on_remove_tc3_message(b)
    await _drain()
    assert [f["header"]["tr_type"] for f in real._ws.frames] == ["1", "2"]
    real.TC1().on_tc1_message(a)
    await _drain()
    assert [f["header"]["tr_type"] for f in real._ws.frames] == ["1", "2", "1"]


@pytest.mark.asyncio
async def test_futures_unregister_is_not_sent_when_never_registered():
    real = _connected(FuturesReal)
    real._on_message("OVC", lambda r: None)
    real._on_remove_message("OVC")
    await _drain()
    assert real._ws.frames == []


# ---------------------------------------------------------------------------
# K2 — re-registration helper
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("real_cls, family, method, tr_cd", [
    (FuturesReal, "_tc123_connect", "TC1", "TC1"),
    (StockReal, "_as01234_connect", "AS0", "AS1"),
    (KoreaReal, "_sc01234_connect", "SC1", "SC1"),
])
async def test_reregister_resends_active_family_once(real_cls, family, method, tr_cd):
    real = _connected(real_cls)
    assert getattr(real, method)()._parent is real  # the product exposes this account stream
    setattr(real, family, True)
    assert real._reregister_account_events() == [family]
    await _drain()
    frame, = real._ws.frames
    assert frame["header"]["tr_type"] == "1" and frame["body"]["tr_cd"] == tr_cd
    assert getattr(real, family) is True


@pytest.mark.asyncio
async def test_reregister_skips_families_without_listeners():
    real = _connected(StockReal)
    assert real._reregister_account_events() == []
    await _drain()
    assert real._ws.frames == []


def test_option_defaults_to_true_and_is_threaded_through_factories():
    from programgarden_finance.ls.overseas_futureoption import OverseasFutureoption

    tm = _token_manager()
    assert FuturesReal(token_manager=tm)._reregister_account_events_on_reconnect is True
    assert FuturesReal(token_manager=tm, reregister_account_events_on_reconnect=False
                       )._reregister_account_events_on_reconnect is False
    client = OverseasFutureoption(token_manager=tm)
    try:
        real = client.real(reregister_account_events_on_reconnect=False)
        assert real._reregister_account_events_on_reconnect is False
    finally:
        OverseasFutureoption._clear_real_instance(id(tm))


# ---------------------------------------------------------------------------
# K2 — end to end over a local websocket server
# ---------------------------------------------------------------------------

class _DroppingServer:
    """Records frames per connection and drops the first connection on request."""

    def __init__(self):
        self.connections = []
        self.drop_first = asyncio.Event()
        self._server = None
        self.port = None

    async def _handle(self, ws):
        index = len(self.connections)
        frames = []
        self.connections.append(frames)
        drop = asyncio.ensure_future(self.drop_first.wait()) if index == 0 else None
        try:
            while True:
                recv = asyncio.ensure_future(ws.recv())
                waiters = {recv} | ({drop} if drop is not None and not drop.done() else set())
                done, _ = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
                if recv in done:
                    frames.append(json.loads(recv.result()))
                else:
                    recv.cancel()
                if drop is not None and drop.done():
                    await ws.close()
                    return
        except Exception:
            return

    async def __aenter__(self):
        self._server = await serve(self._handle, "localhost", 0)
        self.port = next(iter(self._server.sockets)).getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()

    @property
    def url(self):
        return f"ws://localhost:{self.port}"


async def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return False


def _kinds(frames):
    return [(f["header"]["tr_type"], f["body"]["tr_cd"], (f["body"].get("tr_key") or "").strip())
            for f in frames]


@pytest.mark.asyncio
@pytest.mark.parametrize("reregister", [True, False])
async def test_reconnect_restores_market_and_account_registrations(reregister):
    async with _DroppingServer() as server:
        real = FuturesReal(token_manager=_token_manager(server.url), max_backoff=1.0,
                           reregister_account_events_on_reconnect=reregister)
        try:
            await real.connect(timeout=5.0)
            real.OVC().add_ovc_symbols(["HMHU26"])
            real.TC1().on_tc1_message(lambda resp: None)
            assert await _wait_for(lambda: len(server.connections[0]) == 2)
            assert sorted(_kinds(server.connections[0])) == [("1", "TC1", ""), ("3", "OVC", "HMHU26")]

            server.drop_first.set()
            expected = 2 if reregister else 1
            assert await _wait_for(lambda: len(server.connections) == 2
                                   and len(server.connections[1]) >= expected)
            await asyncio.sleep(0.1)  # nothing further should arrive
            second = _kinds(server.connections[1])
            # Market data first, then the account registration (when enabled).
            assert second[0] == ("3", "OVC", "HMHU26")
            if reregister:
                assert second == [("3", "OVC", "HMHU26"), ("1", "TC1", "")]
            else:
                assert second == [("3", "OVC", "HMHU26")]
            # With the option off the flag is left as it was (pre-K2 behaviour): the SDK
            # then assumes LS kept the registration, which phase-0 F3 (paper futures,
            # 2026-10-15) showed it does not — hence the default of True.
            assert real._tc123_connect is True
        finally:
            await real.close(force=True)

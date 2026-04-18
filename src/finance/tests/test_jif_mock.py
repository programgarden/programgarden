"""Offline JIF pipeline tests using MockJIFServer.

EN:
    Exercises the full Phase 1 pipeline (RealJIF ↔ real_base
    _add_message_symbols/_on_message_listeners ↔ JIFRealResponse
    parsing ↔ snapshot cache) without a live LS connection. Scenarios
    cover the happy path, circuit breakers, extended-hours transitions,
    the empty-snapshot / timeout path, and unsubscribe behaviour.

KO:
    라이브 LS 연결 없이 Phase 1 전체 파이프라인을 검증합니다. 정규장 개장,
    서킷브레이커, 프리마켓 전이, 미수신 시 스냅샷 비어있음, 구독 해제
    까지 mock 서버 시나리오 기반으로 전수 검증.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, List

import pytest

# tests/ is a flat directory (no __init__.py) — add it to sys.path so the
# sibling `mocks` package is importable as an absolute module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from programgarden_finance.ls.common import Common
from programgarden_finance.ls.common.real.JIF.blocks import JIFRealResponse
from programgarden_finance.ls.token_manager import TokenManager

from mocks import (  # noqa: E402 — sys.path manipulation required above
    MockJIFServer,
    scenario_circuit_breaker,
    scenario_extended_hours,
    scenario_kr_opening_sequence,
    scenario_timeout,
    scenario_weekday_us_open_kr_close,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_stub_token_manager(wss_url: str) -> TokenManager:
    """TokenManager bypassing the OAuth flow — tests only need access_token + wss_url."""

    tm = TokenManager()
    tm.access_token = "stub-access-token"
    tm.token_type = "Bearer"
    tm.expires_in = 86400
    # acquired_at is a ClassVar in the dataclass; set directly to prevent
    # is_expired() from returning True during the test window.
    TokenManager.acquired_at = time.time()
    tm.wss_url = wss_url
    return tm


async def _wait_until(predicate, timeout: float = 2.0, interval: float = 0.02):
    """Await until ``predicate()`` is truthy or ``timeout`` elapses."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


async def _open_jif_client(wss_url: str):
    """Build (TokenManager, Common, Real, listener_events) tuple for tests.

    Each call creates fresh Common/Real singletons keyed by the new
    TokenManager instance — tests remain isolated.
    """

    tm = _make_stub_token_manager(wss_url)
    common = Common(token_manager=tm)
    real = common.real()
    await real.connect()
    return tm, common, real


async def _teardown(common: Common, real, tm: TokenManager) -> None:
    try:
        await real.close(force=True)
    except Exception:
        pass
    Common._clear_real_instance(id(tm))


# ---------------------------------------------------------------------------
# Core pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_request_uses_correct_tr_fields():
    async with MockJIFServer(scenario_timeout) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            ok = await _wait_until(lambda: bool(server.received_messages))
            assert ok, "subscribe request never reached the mock server"

            msg = server.received_messages[0]
            assert msg["header"]["tr_type"] == "3"
            assert msg["body"]["tr_cd"] == "JIF"
            assert msg["body"]["tr_key"] == "0"
            assert msg["header"]["token"] == "stub-access-token"

            jif.on_remove_jif_message()
            ok = await _wait_until(
                lambda: any(
                    m["header"].get("tr_type") == "4"
                    for m in server.received_messages
                )
            )
            assert ok, "unsubscribe request never reached the mock server"
        finally:
            await _teardown(common, real, tm)


@pytest.mark.asyncio
async def test_weekday_scenario_updates_snapshot():
    events: List[JIFRealResponse] = []

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: events.append(resp))

            ok = await _wait_until(lambda: len(jif.get_snapshot()) >= 5, timeout=3.0)
            assert ok, f"snapshot incomplete: {jif.get_snapshot()}"

            snap = jif.get_snapshot()
            # US open
            us_state = snap.get("9")
            assert us_state is not None
            assert us_state["market"] == "US"
            assert us_state["jstatus"] == "21"
            assert us_state["is_regular_open"] is True
            assert us_state["label"] == "Market open"

            # KOSPI closed
            kospi_state = snap.get("1")
            assert kospi_state is not None
            assert kospi_state["market"] == "KOSPI"
            assert kospi_state["jstatus"] == "41"
            assert kospi_state["is_regular_open"] is False
            assert kospi_state["label"] == "Market closed"

            # convenience helper
            assert jif.get_market_state("US")["jstatus"] == "21"
            assert jif.get_market_state("KOSPI")["jstatus"] == "41"

            # user listener received every broadcast event
            assert len(events) >= 5
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


@pytest.mark.asyncio
async def test_kr_opening_sequence_keeps_latest_status():
    async with MockJIFServer(scenario_kr_opening_sequence) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            ok = await _wait_until(
                lambda: jif.get_market_state("KOSPI")
                and jif.get_market_state("KOSPI")["jstatus"] == "21",
                timeout=3.0,
            )
            assert ok, (
                "KOSPI should end at jstatus=21 after the opening sequence, "
                f"got {jif.get_market_state('KOSPI')}"
            )
            final = jif.get_market_state("KOSPI")
            assert final["is_regular_open"] is True
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


@pytest.mark.asyncio
async def test_circuit_breaker_transition_marks_closed():
    async with MockJIFServer(scenario_circuit_breaker) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            # wait for final CB state
            ok = await _wait_until(
                lambda: jif.get_market_state("KOSPI")
                and jif.get_market_state("KOSPI")["jstatus"] == "61",
                timeout=3.0,
            )
            assert ok, f"CB transition missing: {jif.get_snapshot()}"

            state = jif.get_market_state("KOSPI")
            assert state["label"] == "Circuit breaker level 1"
            assert state["is_regular_open"] is False
            assert state["is_extended_open"] is False
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


@pytest.mark.asyncio
async def test_extended_hours_distinguishes_regular_vs_extended():
    async with MockJIFServer(scenario_extended_hours) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            # Final expected state: Market open (21) — both flags True
            ok = await _wait_until(
                lambda: jif.get_market_state("US")
                and jif.get_market_state("US")["jstatus"] == "21",
                timeout=3.0,
            )
            assert ok, f"US did not reach jstatus=21: {jif.get_snapshot()}"

            final = jif.get_market_state("US")
            assert final["is_regular_open"] is True
            assert final["is_extended_open"] is True
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


@pytest.mark.asyncio
async def test_timeout_scenario_leaves_snapshot_empty():
    async with MockJIFServer(scenario_timeout) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            # Give the server ~200ms to prove no events will arrive.
            await asyncio.sleep(0.2)
            assert jif.get_snapshot() == {}, (
                f"Unexpected events under timeout scenario: {jif.get_snapshot()}"
            )
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


# ---------------------------------------------------------------------------
# Listener error isolation
# ---------------------------------------------------------------------------


class _Boom(RuntimeError):
    pass


@pytest.mark.asyncio
async def test_user_listener_exception_does_not_break_pipeline():
    received_after_boom: List[JIFRealResponse] = []

    call_count = 0

    def listener(resp: JIFRealResponse) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _Boom("user listener broke")
        received_after_boom.append(resp)

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(listener)

            ok = await _wait_until(lambda: call_count >= 5, timeout=3.0)
            assert ok, f"pipeline stopped delivering after boom (calls={call_count})"
            # Snapshot updates happen before the listener dispatch, so the
            # boom on call 1 must not prevent subsequent snapshots. Allow a
            # small drain window to flush any in-flight dispatches.
            await _wait_until(lambda: len(jif.get_snapshot()) >= 5, timeout=1.0)
            assert len(jif.get_snapshot()) >= 4, (
                f"pipeline did not recover after boom; snapshot={jif.get_snapshot()}"
            )
            # listener kept being called after the boom (exception isolated)
            assert len(received_after_boom) >= 3
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)


# ---------------------------------------------------------------------------
# Unknown code safety — overseas-futures exchange values should not crash
# ---------------------------------------------------------------------------


async def _scenario_unknown_jangubun(ws) -> None:
    """Simulate an unexpected jangubun (e.g., someone adding overseas futures
    outside the 12 supported markets). The client must ignore the code
    safely — snapshot records raw jangubun, resolve_market falls back to
    the raw code, and SUPPORTED_MARKETS check can catch it."""

    payload = {
        "header": {
            "tr_cd": "JIF",
            "tr_key": "0",
            "tr_type": "3",
            "rsp_cd": "00000",
        },
        "body": {"jangubun": "G", "jstatus": "21"},
    }
    await asyncio.sleep(0.02)
    await ws.send(__import__("json").dumps(payload))


@pytest.mark.asyncio
async def test_unsupported_jangubun_snapshotted_but_outside_supported_markets():
    from programgarden_finance.ls.common.real.JIF.constants import (
        SUPPORTED_MARKETS,
    )

    async with MockJIFServer(_scenario_unknown_jangubun) as server:
        tm, common, real = await _open_jif_client(server.wss_url)
        try:
            jif = real.JIF()
            jif.on_jif_message(lambda resp: None)

            ok = await _wait_until(lambda: "G" in jif.get_snapshot(), timeout=2.0)
            assert ok, f"unknown code was not snapshotted: {jif.get_snapshot()}"

            entry = jif.get_snapshot()["G"]
            # resolve_market returns the raw code when unknown
            assert entry["market"] == "G"
            # and it is *not* part of the canonical supported markets
            assert entry["market"] not in SUPPORTED_MARKETS
            jif.on_remove_jif_message()
        finally:
            await _teardown(common, real, tm)

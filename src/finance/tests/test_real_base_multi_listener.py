"""real_base 리스너 레지스트리 — 키(TR)당 다중 리스너 (1.9.7).

배경: 1.9.6 까지 `_on_message` 가 `dict[key] = listener` 단일 대입이라 같은 Real 객체에 두 경로가
같은 TR 을 걸면 나중 것이 앞의 것을 조용히 지웠다(엔진 체결 원장 구독 vs 주문이벤트 노드 마스터,
2026-09-12 국내 SC1 회귀 실측). 이 테스트는 그 계약을 고정한다.
"""
import asyncio

import pytest

from programgarden_finance.ls.korea_stock.real import Real as KoreaReal
from programgarden_finance.ls.token_manager import TokenManager


def _real() -> KoreaReal:
    real = KoreaReal(token_manager=TokenManager())  # 네트워크 없음 — 레지스트리만 본다
    real._connected_event.set()  # _on_message 는 연결 전엔 RuntimeError
    return real


def test_two_listeners_on_same_key_both_survive():
    real = _real()
    a, b = (lambda r: None), (lambda r: None)
    real._on_message("SC1", a)
    real._on_message("SC1", b)
    assert real._on_message_listeners["SC1"] == [a, b]


def test_same_listener_registered_twice_is_kept_once():
    real = _real()
    a = lambda r: None  # noqa: E731
    real._on_message("SC1", a)
    real._on_message("SC1", a)
    assert real._on_message_listeners["SC1"] == [a]


def test_remove_specific_listener_keeps_the_other():
    real = _real()
    a, b = (lambda r: None), (lambda r: None)
    real._on_message("SC1", a)
    real._on_message("SC1", b)
    real._on_remove_message("SC1", a)
    assert real._on_message_listeners["SC1"] == [b]
    # 남은 리스너가 있으므로 계좌 실시간 등록 플래그는 건드리지 않는다
    real._sc01234_connect = True
    real._on_remove_message("SC1", (lambda r: None))  # 미등록 리스너 제거는 무해
    assert real._on_message_listeners["SC1"] == [b]
    assert real._sc01234_connect is True


def test_remove_without_listener_clears_whole_key_backward_compatible(monkeypatch):
    real = _real()
    # 마지막 리스너가 사라지면 계좌 실시간 해제를 시도한다 — 소켓이 없으므로 그 부분만 막는다
    monkeypatch.setattr(real, "_remove_real_order_korea", lambda: None)
    monkeypatch.setattr(real, "_remove_real_order", lambda: None)
    a, b = (lambda r: None), (lambda r: None)
    real._on_message("SC1", a)
    real._on_message("SC1", b)
    real._on_remove_message("SC1")
    assert "SC1" not in real._on_message_listeners


def test_last_listener_removed_resets_order_flags(monkeypatch):
    real = _real()
    a = lambda r: None  # noqa: E731
    real._on_message("SC1", a)
    real._sc01234_connect = True
    real._as01234_connect = True
    called = []
    monkeypatch.setattr(real, "_remove_real_order_korea", lambda: called.append("kr"))
    monkeypatch.setattr(real, "_remove_real_order", lambda: called.append("os"))
    real._on_remove_message("SC1", a)
    assert real._on_message_listeners == {}
    assert real._sc01234_connect is False and real._as01234_connect is False
    assert set(called) == {"kr", "os"}


@pytest.mark.asyncio
async def test_dispatch_reaches_every_listener_sync_and_async():
    real = _real()
    got = []
    done = asyncio.Event()

    def sync_listener(resp):
        got.append(("sync", resp))

    async def async_listener(resp):
        got.append(("async", resp))
        done.set()

    real._on_message("SC1", sync_listener)
    real._on_message("SC1", async_listener)
    loop = asyncio.get_running_loop()
    for fn in list(real._on_message_listeners["SC1"]):
        real._dispatch_to_listener(loop, fn, "frame")
    await asyncio.wait_for(done.wait(), 2)
    # sync 리스너는 threadpool 로 넘어가므로 잠깐 양보
    for _ in range(50):
        if len(got) == 2:
            break
        await asyncio.sleep(0.02)
    assert sorted(got) == [("async", "frame"), ("sync", "frame")]

"""runtime: 계좌 추적기의 별도 LS 인스턴스도 `context.ls_token_provider` 를 상속한다 (2026-08-29).

`tests/test_dry_run_skips_account_tracking.py` 가 dry_run 쪽(추적기 skip)을 고정하고, 이 파일은
runtime 쪽 갭을 고정한다 — 2026-08-29 이전엔 `_start_account_tracking` 이 맨손 `LS()` 로
appkey/appsecret 직접 로그인해, 서버 단일 발급 토큰 + 더미 appsecret 으로 도는 기기(트레이앱
검증 잡·서버 발급 모드)의 **실제 실행**에서 추적기만 403 으로 죽었다(error 로그 뒤 추적 없음).
`LSClientManager.get_or_create`(노드 공용 인스턴스)와 같은 부착 규칙을 공유 헬퍼로 쓴다.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from programgarden import executor as ex
from programgarden.context import ExecutionContext
from programgarden.executor import BrokerNodeExecutor, LSClientManager, attach_context_token_provider


class _FakeLS:
    """`programgarden_finance.LS` 대역 — 공급자 등록·로그인 순서를 기록한다."""

    instances: list["_FakeLS"] = []

    def __init__(self) -> None:
        self.provider = None
        self.events: list[str] = []
        self.login_kwargs: dict | None = None
        _FakeLS.instances.append(self)

    def set_token_provider(self, *, provider) -> None:
        self.provider = provider
        self.events.append("set_token_provider")

    def login(self, **kwargs) -> bool:
        self.events.append("login")
        self.login_kwargs = kwargs
        return True

    def is_logged_in(self) -> bool:
        return "login" in self.events


def _ctx(provider=None) -> ExecutionContext:
    ctx = ExecutionContext(job_id="j", workflow_id="wf", context_params={"dry_run": False},
                           ls_token_provider=provider)
    assert ctx.is_dry_run is False
    return ctx


def _provider_calls():
    calls: list[tuple] = []

    def provider(appkey, product, paper_trading, *, force_reissue=False, stale_token=None):
        calls.append((appkey, product, paper_trading, force_reissue, stale_token))
        return "SERVER-TOKEN", 4102444800.0

    return provider, calls


@pytest.fixture(autouse=True)
def _reset():
    _FakeLS.instances.clear()
    LSClientManager.reset()
    yield
    LSClientManager.reset()


@pytest.mark.asyncio
async def test_account_tracker_attaches_provider_before_login():
    provider, calls = _provider_calls()
    ctx = _ctx(provider)
    with patch("programgarden_finance.LS", _FakeLS), \
         patch.object(BrokerNodeExecutor, "_start_overseas_stock_tracker", new=AsyncMock()) as tracker:
        await BrokerNodeExecutor()._start_account_tracking(
            "broker", "overseas_stock", "ls", "AK", "dummy-secret", True, ctx,
        )
    assert len(_FakeLS.instances) == 1
    ls = _FakeLS.instances[0]
    assert ls.events == ["set_token_provider", "login"]  # 부착이 로그인보다 먼저
    assert ls.login_kwargs == {"appkey": "AK", "appsecretkey": "dummy-secret", "paper_trading": True}
    tracker.assert_awaited_once()
    # 바인딩된 공급자는 이 인스턴스의 appkey/product/paper 로 서버에 묻는다
    assert ls.provider() == ("SERVER-TOKEN", 4102444800.0)
    assert calls == [("AK", "overseas_stock", True, False, None)]


@pytest.mark.asyncio
async def test_account_tracker_without_provider_keeps_self_issue_path():
    ctx = _ctx(None)
    with patch("programgarden_finance.LS", _FakeLS), \
         patch.object(BrokerNodeExecutor, "_start_overseas_futures_tracker", new=AsyncMock()) as tracker:
        await BrokerNodeExecutor()._start_account_tracking(
            "broker", "overseas_futures", "ls", "AK", "real-secret", False, ctx,
        )
    ls = _FakeLS.instances[0]
    assert ls.events == ["login"] and ls.provider is None
    tracker.assert_awaited_once()


def test_helper_forwards_force_reissue_only_when_provider_accepts_it():
    provider, calls = _provider_calls()
    ctx = _ctx(provider)
    ls = _FakeLS()
    assert attach_context_token_provider(ls, ctx, appkey="AK", product="korea_stock",
                                         paper_trading=False, node_id="n") is True
    ls.provider(force_reissue=True, stale_token="DEAD")
    assert calls[-1] == ("AK", "korea_stock", False, True, "DEAD")

    # 구판 3-인자 공급자 — 키워드를 넘기지 않는다(TypeError 없이 통과)
    legacy_calls: list[tuple] = []

    def legacy(appkey, product, paper_trading):
        legacy_calls.append((appkey, product, paper_trading))
        return "T", 0.0

    ls2 = _FakeLS()
    assert attach_context_token_provider(ls2, _ctx(legacy), appkey="AK", product="overseas_stock",
                                         paper_trading=True) is True
    ls2.provider(force_reissue=True, stale_token="DEAD")
    assert legacy_calls == [("AK", "overseas_stock", True)]

    # 공급자 없음 → 부착하지 않는다
    ls3 = _FakeLS()
    assert attach_context_token_provider(ls3, _ctx(None), appkey="AK", product="overseas_stock",
                                         paper_trading=True) is False
    assert ls3.events == []


def test_client_manager_and_tracker_share_the_same_attach_rule():
    """노드 공용 인스턴스(get_or_create)도 같은 헬퍼로 부착한다 — 리팩터 회귀 가드."""
    provider, calls = _provider_calls()
    ctx = _ctx(provider)
    with patch("programgarden_finance.LS", _FakeLS):
        ls, ok, err = LSClientManager.get_or_create(
            product="overseas_stock", appkey="AK", appsecret="dummy", paper_trading=True,
            context=ctx, node_id="n",
        )
    assert ok and err is None
    assert ls.events == ["set_token_provider", "login"]
    assert ls.provider() == ("SERVER-TOKEN", 4102444800.0)
    assert calls == [("AK", "overseas_stock", True, False, None)]

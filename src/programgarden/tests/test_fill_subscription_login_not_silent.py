"""체결 이벤트 구독 로그인 실패는 조용히 넘어가지 않는다 (M2, 2026-09-12 prod 실관측).

관측된 사고
-----------
prod 파드가 LS OpenAPI 접속 불가 중에 떴다. ``Token 요청 실패`` 2건 뒤 브로커 노드가
**completed** 로 끝났고, ``_subscribe_workflow_fill_events`` 는
``if not success: context.log("error", ...); return`` 으로 체결 구독을 건너뛰고
반환했다. 그 파드는 실시간 체결을 영영 받지 못하는데, 주문 노드는
``LSClientManager.get_or_create`` 가 매번 재로그인을 시도하므로 **주문은 나갈 수
있다** — 주문은 나가는데 체결은 원장에 안 잡히는 조합이다(FIFO 포지션·손익·리스크
판정이 전부 눈먼 상태).

고친 방침 (가)+(나)
-------------------
(가) 제한된 재시도: ``_FILL_SUBSCRIPTION_LOGIN_RETRY_DELAYS`` 만큼만 백오프 재시도한다.
     상한을 두는 이유는 LS 앱키가 공유 자원이고 토큰 발급에 전송수 제한이 있어서다.
(나) 그래도 실패하면 **노드 실패로 올린다** + 투자자 알림(CRITICAL)을 낸다.
     ``context.log("error")`` 는 stdout 에 남지 않으므로 알림 채널로도 드러낸다.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, patch

from programgarden.context import ExecutionContext
from programgarden.executor import BrokerNodeExecutor
from programgarden_core.bases.listener import (
    BaseExecutionListener,
    NotificationCategory,
    NotificationSeverity,
    WorkflowPnLEvent,
)
from programgarden_core.exceptions import ExecutionError


class _PnLListener(BaseExecutionListener):
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:  # pragma: no cover
        pass


class FakeContext:
    """``_subscribe_workflow_fill_events`` 가 실제로 쓰는 표면만 구현."""

    is_dry_run = False
    is_shutdown = False

    def __init__(self):
        self.logs = []
        self.notifications = []

    def log(self, level, message, node_id=None, data=None):
        self.logs.append((level, message))

    async def send_notification(self, **kwargs):
        self.notifications.append(kwargs)


@pytest.fixture
def no_real_sleep(monkeypatch):
    """백오프 대기를 기록만 하고 실제로 자지 않는다."""
    slept = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay, *args, **kwargs):
        slept.append(delay)
        return await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return slept


async def _subscribe(context, login_results):
    """``ensure_ls_login`` 이 주어진 순서대로 응답하게 하고 구독을 돌린다."""
    calls = []

    def fake_login(appkey, appsecret, paper_trading, ctx, node_id, product, caller_name=""):
        calls.append(product)
        return login_results[min(len(calls) - 1, len(login_results) - 1)]

    with patch("programgarden.executor.ensure_ls_login", side_effect=fake_login), \
         patch.object(BrokerNodeExecutor, "_subscribe_overseas_futures_fill_events",
                      new=AsyncMock()) as subscribe:
        await BrokerNodeExecutor()._subscribe_workflow_fill_events(
            node_id="broker", product="overseas_futures",
            appkey="k", appsecret="s", paper_trading=False, context=context,
        )
    return calls, subscribe


@pytest.mark.asyncio
async def test_login_failure_retries_with_bounded_backoff_then_raises(no_real_sleep):
    """로그인이 계속 실패하면 (가) 제한 재시도 후 (나) 노드 실패로 올린다."""
    context = FakeContext()

    with pytest.raises(ExecutionError) as ei:
        await _subscribe(context, [(None, False, "Token 요청 실패")])

    # 재시도는 유한하다 — 최초 1회 + 백오프 2회(간격 2s·5s, 누적 7초).
    # 🔴 리터럴로 고정한다: 클래스 상수 _FILL_SUBSCRIPTION_LOGIN_RETRY_DELAYS 를
    #    그대로 참조하면 상수가 (2.0, 5.0, 10.0) 처럼 늘어나도 비교 대상도 같이
    #    늘어나 상한 초과를 못 잡는다(검증 에이전트 지적). 관측된 sleep 간격을
    #    하드코딩된 기대값과 대조해야 상한이 진짜로 고정된다.
    assert no_real_sleep == [2.0, 5.0], "백오프 간격/횟수가 상한을 벗어났다 (3회/누적 7초 초과)"
    assert len(no_real_sleep) == 2, "재시도 횟수가 2회(백오프 길이)를 벗어났다"
    assert "구독" in str(ei.value)


@pytest.mark.asyncio
async def test_login_failure_is_not_a_silent_completion(no_real_sleep):
    """조용한 완료 금지 — 에러 로그 + 투자자 알림(CRITICAL)이 둘 다 남는다."""
    context = FakeContext()

    with pytest.raises(ExecutionError):
        await _subscribe(context, [(None, False, "Token 요청 실패")])

    assert any(level == "error" for level, _ in context.logs)
    assert len(context.notifications) == 1
    note = context.notifications[0]
    assert note["category"] == NotificationCategory.CONNECTION_FAILED
    assert note["severity"] == NotificationSeverity.CRITICAL
    assert note["data"]["product"] == "overseas_futures"


@pytest.mark.asyncio
async def test_login_recovering_on_retry_subscribes_without_failing(no_real_sleep):
    """1회차 실패 → 2회차 성공이면 구독을 정상 진행하고 노드를 실패시키지 않는다."""
    context = FakeContext()

    calls, subscribe = await _subscribe(
        context,
        [(None, False, "Token 요청 실패"), (object(), True, None)],
    )

    assert len(calls) == 2, "재시도가 실제로 재로그인을 호출해야 한다"
    subscribe.assert_awaited_once()
    assert no_real_sleep == [BrokerNodeExecutor._FILL_SUBSCRIPTION_LOGIN_RETRY_DELAYS[0]]
    assert context.notifications == []


@pytest.mark.asyncio
async def test_subscription_error_after_login_also_raises(no_real_sleep):
    """로그인은 됐는데 구독 자체가 실패해도 조용히 끝내지 않는다."""
    context = FakeContext()

    def fake_login(*args, **kwargs):
        return object(), True, None

    with patch("programgarden.executor.ensure_ls_login", side_effect=fake_login), \
         patch.object(BrokerNodeExecutor, "_subscribe_overseas_futures_fill_events",
                      new=AsyncMock(side_effect=RuntimeError("websocket refused"))):
        with pytest.raises(ExecutionError) as ei:
            await BrokerNodeExecutor()._subscribe_workflow_fill_events(
                node_id="broker", product="overseas_futures",
                appkey="k", appsecret="s", paper_trading=False, context=context,
            )

    assert "websocket refused" in str(ei.value)
    assert len(context.notifications) == 1


# ── 노드 레벨: 브로커 노드가 completed 로 끝나지 않는다 ──────────────────────


def _ctx(dry_run: bool, tmp_path) -> ExecutionContext:
    ctx = ExecutionContext(
        job_id="j", workflow_id="wf",
        context_params={"dry_run": dry_run}, storage_dir=str(tmp_path),
    )
    ctx.add_listener(_PnLListener())
    assert ctx.is_dry_run is dry_run
    return ctx


@pytest.mark.asyncio
async def test_broker_node_fails_when_fill_subscription_login_fails(no_real_sleep, tmp_path):
    """브로커 노드가 connected=True 를 돌려주며 조용히 완료되지 않는다."""
    ctx = _ctx(False, tmp_path)

    with patch("programgarden.executor.ensure_ls_login",
               side_effect=lambda *a, **k: (None, False, "Token 요청 실패")), \
         patch.object(BrokerNodeExecutor, "_start_account_tracking", new=AsyncMock()), \
         patch.object(BrokerNodeExecutor, "_sync_fill_prices_from_history", new=AsyncMock()):
        with pytest.raises(ExecutionError):
            await BrokerNodeExecutor().execute(
                "broker", "OverseasStockBrokerNode",
                {"appkey": "k", "appsecret": "s", "paper_trading": False}, ctx,
            )


@pytest.mark.asyncio
async def test_dry_run_broker_does_not_attempt_fill_subscription(tmp_path):
    """dry_run 은 구독 자체를 시도하지 않는다 (모의 실행엔 체결이 없다).

    이 게이트가 없으면 더미 appsecret 으로 도는 검증 잡이 위 하드 실패에 걸린다 —
    같은 이유로 계좌 추적·체결내역 동기화는 이미 dry_run 에서 skip 이다.
    """
    ctx = _ctx(True, tmp_path)

    with patch.object(BrokerNodeExecutor, "_subscribe_workflow_fill_events",
                      new=AsyncMock()) as subscribe, \
         patch.object(BrokerNodeExecutor, "_start_account_tracking", new=AsyncMock()), \
         patch.object(BrokerNodeExecutor, "_sync_fill_prices_from_history", new=AsyncMock()):
        out = await BrokerNodeExecutor().execute(
            "broker", "OverseasStockBrokerNode",
            {"appkey": "k", "appsecret": "s", "paper_trading": False}, ctx,
        )

    subscribe.assert_not_awaited()
    assert out["connected"] is True

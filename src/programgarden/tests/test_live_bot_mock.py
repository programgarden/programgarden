"""live_bot workflow (Phase 4) Mock 기반 E2E 라우팅 검증.

Plan: .claude/pg-plans/20260418-jif-market-status-plan.md (Phase 4)

실계좌(LS증권)/텔레그램 실접속 없이, MockJIFServer 를 통해 JIF 이벤트를
push 하고 live_bot workflow 의 핵심 라우팅 결정을 검증합니다:

1. 미국장 개장 (us_is_open=true) → IfNode(if_us_open) true 브랜치 →
   sell_items → sell_order 경로 활성화
2. 미국장 서킷브레이커/휴장 (us_is_open=false) → IfNode false 브랜치 →
   telegram_market_closed 경로 활성화
3. 이벤트 수신 전 초기 상태 (us_is_open=None) → `== true` 평가 False →
   보수적으로 매도 주문 스킵 (주말 오주문 방지)
4. ScalableTrailingStop 플러그인 롤백 검증 — 더 이상 NYSE 시간 로직
   내부에 포함하지 않음. passed_symbols 는 HWM/trail 계산만으로 결정.

WorkflowExecutor 전체를 돌리지 않고, MarketStatusNodeExecutor +
IfNodeExecutor + 플러그인 함수를 직접 호출하는 isolated 통합 구조.
외부 I/O 노드(BrokerNode/RealAccountNode/OrderNode/TelegramNode) 는
목적상 검증 범위 밖.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# finance mocks import path
FINANCE_TESTS = Path(__file__).resolve().parents[2] / "finance" / "tests"
sys.path.insert(0, str(FINANCE_TESTS))

# live_bot 플러그인 import path
LIVE_BOT = Path(__file__).resolve().parents[3] / "scripts" / "live_bot"
sys.path.insert(0, str(LIVE_BOT))

from mocks import (  # noqa: E402
    MockJIFServer,
    scenario_circuit_breaker,
    scenario_timeout,
    scenario_weekday_us_open_kr_close,
)

from programgarden.context import ExecutionContext  # noqa: E402
from programgarden.executor import (  # noqa: E402
    IfNodeExecutor,
    LSClientManager,
    MarketStatusNodeExecutor,
)
from programgarden_finance.ls.token_manager import TokenManager  # noqa: E402

from plugins.scalable_trailing_stop import (  # noqa: E402
    SCHEMA,
    scalable_trailing_stop_condition,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class _StubLS:
    """LSClientManager 가 재사용할 최소 LS instance."""

    def __init__(self, wss_url: str):
        tm = TokenManager()
        tm.access_token = "stub-access-token"
        tm.token_type = "Bearer"
        tm.expires_in = 86400
        TokenManager.acquired_at = time.time()
        tm.wss_url = wss_url
        self.token_manager = tm

    def is_logged_in(self) -> bool:
        return True


def _install_stub_ls(product: str, wss_url: str) -> _StubLS:
    stub = _StubLS(wss_url)
    LSClientManager._instances[product] = stub
    LSClientManager._credentials[product] = ("stub-appkey", "stub-secret", False)
    return stub


def _build_context(outputs: Dict[str, Dict[str, Any]] | None = None) -> ExecutionContext:
    ctx = ExecutionContext(
        job_id=f"job-{time.time_ns()}", workflow_id="wf-live-bot-mock"
    )
    for node_id, ports in (outputs or {}).items():
        for port, value in ports.items():
            ctx.set_output(node_id, port, value)
    return ctx


def _ms_config(**overrides: Any) -> Dict[str, Any]:
    base = {
        "connection": {
            "appkey": "stub-appkey",
            "appsecret": "stub-secret",
            "paper_trading": False,
            "product": "overseas_stock",
        },
        "markets": ["US"],
        "stay_connected": True,
        "include_extended_hours": False,
        "_trigger_on_update_nodes": [],
    }
    base.update(overrides)
    return base


async def _wait_until(predicate, timeout: float = 3.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


async def _eval_if_us_open(ctx: ExecutionContext) -> Dict[str, Any]:
    """live_bot 의 `if_us_open` IfNode 를 동일 config 로 평가."""

    executor = IfNodeExecutor()
    return await executor.execute(
        node_id="if_us_open",
        node_type="IfNode",
        config={
            "left": "{{ nodes.market_status.us_is_open }}",
            "operator": "==",
            "right": True,
        },
        context=ctx,
    )


@pytest.fixture(autouse=True)
def _reset_ls_manager():
    LSClientManager.reset()
    MarketStatusNodeExecutor._active_subscriptions.clear()
    yield
    LSClientManager.reset()
    MarketStatusNodeExecutor._active_subscriptions.clear()


# ---------------------------------------------------------------------------
# 1. 개장 시나리오: us_is_open=true → sell_order 경로
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us_open_routes_to_sell_branch():
    """weekday_us_open 시나리오 — JIF 가 us_is_open=True push →
    if_us_open true 브랜치 활성화 → sell_order 경로로 라우팅."""

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()

        ms_executor = MarketStatusNodeExecutor()
        try:
            await ms_executor.execute(
                node_id="market_status",
                node_type="MarketStatusNode",
                config=_ms_config(),
                context=ctx,
            )
            assert await _wait_until(
                lambda: ctx.get_output("market_status", "us_is_open") is True,
                timeout=3.0,
            ), "mock server 가 us_is_open=True push 해야 함"

            if_result = await _eval_if_us_open(ctx)

            assert if_result["result"] is True
            assert if_result["_if_branch"] == "true"
            # 캐스케이딩: true 브랜치 활성 → sell_items → sell_order → telegram_sell
            # false 포트 (telegram_market_closed) 는 None (비활성)
            assert if_result["false"] is None
        finally:
            await ms_executor.cleanup_jif_subscriptions(ctx.job_id)


# ---------------------------------------------------------------------------
# 2. 휴장/CB 시나리오: us_is_open=false → telegram_market_closed 경로
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us_closed_via_circuit_breaker_routes_to_market_closed_branch():
    """circuit_breaker 시나리오 — KOSPI CB 이벤트는 KOSPI 상태만 바꾸지만
    US 시장은 이벤트 없음. 이벤트 없는 상태 (None) 에서 IfNode 평가 →
    False → false 브랜치로 라우팅."""

    async with MockJIFServer(scenario_circuit_breaker) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()

        ms_executor = MarketStatusNodeExecutor()
        try:
            await ms_executor.execute(
                node_id="market_status",
                node_type="MarketStatusNode",
                config=_ms_config(markets=["US", "KOSPI"]),
                context=ctx,
            )
            # CB 시나리오는 KOSPI 이벤트만 발생 → us_is_open 은 None 유지
            assert await _wait_until(
                lambda: ctx.get_market_status("KOSPI") is not None, timeout=3.0
            )

            if_result = await _eval_if_us_open(ctx)

            # None == True → False → false 브랜치
            assert if_result["result"] is False
            assert if_result["_if_branch"] == "false"
            assert if_result["true"] is None
        finally:
            await ms_executor.cleanup_jif_subscriptions(ctx.job_id)


# ---------------------------------------------------------------------------
# 3. 초기 상태 (이벤트 미수신): 보수적으로 skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initial_us_is_open_routes_conservatively_to_skip():
    """JIF 이벤트가 한 번도 수신되지 않은 초기 상태 — executor 는
    stay_connected=True 초기 반환 시 us_is_open 등 bool 포트를 False 로
    초기화. IfNode `== true` 평가 False → telegram_market_closed 경로.
    주말/장외 시간 가동 시 오주문 방지 보수적 기본값 (None 이든 False 든
    동일 결과)."""

    async with MockJIFServer(scenario_timeout) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()

        ms_executor = MarketStatusNodeExecutor()
        try:
            await ms_executor.execute(
                node_id="market_status",
                node_type="MarketStatusNode",
                config=_ms_config(),
                context=ctx,
            )
            # timeout 시나리오: JIF 이벤트 없음. executor 의 초기 반환 기본값
            # 은 False (None 취급과 동일 결과)
            await asyncio.sleep(0.3)
            initial_us = ctx.get_output("market_status", "us_is_open")
            assert initial_us in (None, False), (
                f"이벤트 미수신 초기값은 None 또는 False 여야 함 (got {initial_us!r})"
            )
            # 캐시에는 US 상태 없어야 함 (timeout 시나리오)
            assert ctx.get_market_status("US") is None

            if_result = await _eval_if_us_open(ctx)

            assert if_result["result"] is False
            assert if_result["_if_branch"] == "false"
            assert if_result["true"] is None  # sell 경로 비활성
        finally:
            await ms_executor.cleanup_jif_subscriptions(ctx.job_id)


# ---------------------------------------------------------------------------
# 4. 플러그인 롤백 검증 — 시장 시간 로직 제거 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scalable_trailing_stop_plugin_no_market_time_logic():
    """Phase 4.1 롤백 — ScalableTrailingStop 플러그인은 더 이상 NYSE
    시간을 내부 판단하지 않음. HWM 트리거 조건만 충족되면 시장 시간과
    무관하게 passed_symbols 반환. 시장 게이트는 MarketStatusNode 가
    담당."""

    # SCHEMA output_fields 에 market_open / market_closed_triggers 없어야 함
    assert "market_open" not in SCHEMA.output_fields
    assert "market_closed_triggers" not in SCHEMA.output_fields

    # HWM 대비 -10% 낙폭 (stop_ratio 초과) 포지션 주입
    positions = [
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "avg_price": 100.0,
            "current_price": 90.0,  # -10% → 기본 초기 손절 -5% 초과 → trigger
            "quantity": 10,
        }
    ]

    result = await scalable_trailing_stop_condition(
        positions=positions,
        fields={"initial_stop_pct": 5.0, "min_trail_pct": 4.0, "trail_factor": 0.35},
        context=None,
    )

    # 시장 상태와 무관하게 passed_symbols 포함 (이전 버전은 주말엔 빈 배열)
    assert len(result["passed_symbols"]) == 1
    assert result["passed_symbols"][0]["symbol"] == "AAPL"
    assert result["result"] is True

    # 롤백된 키가 리턴 dict 에 남아있지 않음
    assert "market_open" not in result
    assert "market_closed_triggers" not in result
    assert "skipped_due_to_market_closed" not in result.get("analysis", {})


@pytest.mark.asyncio
async def test_scalable_trailing_stop_triggers_reach_passed_symbols():
    """동일 롤백 검증 — passed_symbols 가 effective_passed 분기 없이
    그대로 반환됨을 명시 검증."""

    positions = [
        {
            "symbol": "MSFT",
            "exchange": "NASDAQ",
            "avg_price": 200.0,
            "current_price": 180.0,  # -10% → trigger
            "quantity": 5,
        },
        {
            "symbol": "GOOGL",
            "exchange": "NASDAQ",
            "avg_price": 150.0,
            "current_price": 148.0,  # -1.3% → hold
            "quantity": 3,
        },
    ]

    result = await scalable_trailing_stop_condition(
        positions=positions,
        fields={"initial_stop_pct": 5.0, "min_trail_pct": 4.0, "trail_factor": 0.35},
    )

    passed: List[Dict[str, Any]] = result["passed_symbols"]
    assert len(passed) == 1
    assert passed[0]["symbol"] == "MSFT"
    assert passed[0]["quantity"] == 5

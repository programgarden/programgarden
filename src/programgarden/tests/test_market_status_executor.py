"""Phase 3 통합 테스트 — MarketStatusNodeExecutor + MockJIFServer.

EN:
    Exercises the full Phase 3 pipeline (BrokerNode lookup → LSClientManager
    stub → Common.real connection → JIF subscribe → callback → cache/output
    update → downstream trigger → cleanup) without a live LS environment.
    Re-uses the finance-layer ``MockJIFServer`` introduced in Phase 1.5a.

KO:
    실측 LS 연결 없이 Phase 3 의 BrokerNode 연결 탐색부터 JIF 콜백 → 캐시
    갱신 → 리졸버용 set_output → cleanup 까지 end-to-end 검증. Phase 1.5a
    에서 도입한 `MockJIFServer` 를 재사용합니다.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Make the finance-side mocks importable (tests 디렉토리는 package 가 아님)
FINANCE_TESTS = Path(__file__).resolve().parents[2] / "finance" / "tests"
sys.path.insert(0, str(FINANCE_TESTS))

from mocks import (  # noqa: E402
    MockJIFServer,
    scenario_circuit_breaker,
    scenario_kr_opening_sequence,
    scenario_timeout,
    scenario_weekday_us_open_kr_close,
)

from programgarden.context import ExecutionContext
from programgarden.executor import LSClientManager, MarketStatusNodeExecutor
from programgarden_finance.ls.token_manager import TokenManager


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class _StubLS:
    """Minimal LS instance compatible with LSClientManager reuse path."""

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
    """Inject a stub LS into LSClientManager so executor bypasses real login."""

    stub = _StubLS(wss_url)
    LSClientManager._instances[product] = stub
    LSClientManager._credentials[product] = ("stub-appkey", "stub-secret", False)
    return stub


def _build_context() -> ExecutionContext:
    """Plain ExecutionContext — no data provider required."""

    return ExecutionContext(job_id=f"job-{time.time_ns()}", workflow_id="wf-jif-test")


def _make_config(
    broker_connection: Dict[str, Any],
    *,
    markets: List[str] | None = None,
    stay_connected: bool = True,
    include_extended_hours: bool = False,
    trigger_nodes: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "connection": broker_connection,
        "markets": markets or [],
        "stay_connected": stay_connected,
        "include_extended_hours": include_extended_hours,
        "_trigger_on_update_nodes": trigger_nodes or [],
    }


async def _wait_until(predicate, timeout: float = 3.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


@pytest.fixture(autouse=True)
def _reset_ls_manager():
    """Reset LSClientManager singletons between tests."""

    LSClientManager.reset()
    MarketStatusNodeExecutor._active_subscriptions.clear()
    yield
    LSClientManager.reset()
    MarketStatusNodeExecutor._active_subscriptions.clear()


# ---------------------------------------------------------------------------
# Core integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stay_connected_updates_cache_and_outputs():
    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            stay_connected=True,
        )

        try:
            result = await executor.execute(
                node_id="ms1",
                node_type="MarketStatusNode",
                config=config,
                context=ctx,
            )
            # 초기 반환 — stay_connected 이므로 즉시 반환 (빈 snapshot 가능)
            assert "statuses" in result
            assert "us_is_open" in result
            assert "hk_is_open" in result

            # 이벤트 수신 후 cache + output 갱신 대기
            ok = await _wait_until(
                lambda: len(ctx.get_all_market_statuses()) >= 5, timeout=3.0
            )
            assert ok, f"cache incomplete: {ctx.get_all_market_statuses()}"

            # context cache 에 5개 시장 (US/KOSPI/KOSDAQ/KRX_FUTURES/HK_AM)
            us_status = ctx.get_market_status("US")
            assert us_status is not None
            assert us_status["jstatus"] == "21"
            assert us_status["is_regular_open"] is True
            assert us_status["jstatus_label"] == "Market open"

            kospi_status = ctx.get_market_status("KOSPI")
            assert kospi_status is not None
            assert kospi_status["jstatus"] == "41"
            assert kospi_status["is_regular_open"] is False

            # convenience helper
            assert ctx.is_market_open("US") is True
            assert ctx.is_market_open("KOSPI") is False
            assert ctx.is_market_open("MARS") is None  # never received

            # resolver 경로: set_output 으로 저장된 us_is_open
            us_port = ctx.get_output("ms1", "us_is_open")
            assert us_port is True
            kospi_port = ctx.get_output("ms1", "kospi_is_open")
            assert kospi_port is False

            # statuses 포트는 전체 시장 리스트
            statuses = ctx.get_output("ms1", "statuses")
            assert isinstance(statuses, list)
            assert len(statuses) >= 5
        finally:
            await executor.cleanup_jif_subscriptions(ctx.job_id)


@pytest.mark.asyncio
async def test_markets_filter_limits_cache_updates():
    """markets=['US'] 설정 시 KR 이벤트는 필터링되어 cache 제외."""

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            markets=["US"],
            stay_connected=True,
        )

        try:
            await executor.execute(
                node_id="ms1",
                node_type="MarketStatusNode",
                config=config,
                context=ctx,
            )
            ok = await _wait_until(
                lambda: ctx.get_market_status("US") is not None, timeout=3.0
            )
            assert ok

            # 잠시 추가 대기 — KR 이벤트가 오더라도 무시해야 함
            await asyncio.sleep(0.3)
            statuses = ctx.get_all_market_statuses()
            assert "US" in statuses
            assert "KOSPI" not in statuses
            assert "KOSDAQ" not in statuses
        finally:
            await executor.cleanup_jif_subscriptions(ctx.job_id)


@pytest.mark.asyncio
async def test_stay_connected_false_returns_populated_snapshot():
    """stay_connected=False 는 5초 대기 후 snapshot 반환 + 즉시 해제."""

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            stay_connected=False,
        )

        result = await executor.execute(
            node_id="ms1",
            node_type="MarketStatusNode",
            config=config,
            context=ctx,
        )
        assert isinstance(result["statuses"], list)
        # first event 후 즉시 반환될 수도 있으므로 최소 1개 이상
        assert len(result["statuses"]) >= 1

        # 구독 해제 확인
        assert (
            f"{ctx.job_id}::ms1"
            not in MarketStatusNodeExecutor._active_subscriptions
        )


@pytest.mark.asyncio
async def test_circuit_breaker_marks_market_closed_via_output():
    async with MockJIFServer(scenario_circuit_breaker) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            stay_connected=True,
        )

        try:
            await executor.execute(
                node_id="ms1",
                node_type="MarketStatusNode",
                config=config,
                context=ctx,
            )
            # 최종 CB 상태 도달 대기
            ok = await _wait_until(
                lambda: ctx.get_market_status("KOSPI")
                and ctx.get_market_status("KOSPI")["jstatus"] == "61",
                timeout=3.0,
            )
            assert ok, f"CB transition missing: {ctx.get_all_market_statuses()}"

            kospi_port = ctx.get_output("ms1", "kospi_is_open")
            assert kospi_port is False, "CB 발동 후 kospi_is_open 는 False 여야 함"
        finally:
            await executor.cleanup_jif_subscriptions(ctx.job_id)


@pytest.mark.asyncio
async def test_transition_emits_notification():
    """prev_jstatus != new_jstatus 일 때 send_notification 호출됨."""

    captured_notifications: List[Dict[str, Any]] = []

    async with MockJIFServer(scenario_kr_opening_sequence) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()

        # send_notification 몽키패치로 호출 캡처
        original_send = ctx.send_notification

        async def _capture_send_notification(*args, **kwargs):
            captured_notifications.append(kwargs)
            await original_send(*args, **kwargs)

        ctx.send_notification = _capture_send_notification  # type: ignore[assignment]

        executor = MarketStatusNodeExecutor()
        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            stay_connected=True,
        )

        try:
            await executor.execute(
                node_id="ms1",
                node_type="MarketStatusNode",
                config=config,
                context=ctx,
            )
            ok = await _wait_until(
                lambda: ctx.get_market_status("KOSPI")
                and ctx.get_market_status("KOSPI")["jstatus"] == "21",
                timeout=3.0,
            )
            assert ok
            await asyncio.sleep(0.2)  # transition notification 처리 대기

            assert len(captured_notifications) >= 1, (
                "KOSPI 11→22→...→21 순차 전이 중 최소 한 번은 notification 발행해야 함"
            )
            # 마지막 전이의 data 페이로드
            last = captured_notifications[-1]
            assert "data" in last
            assert last["data"]["market"] == "KOSPI"
            assert last["data"]["jstatus"] == "21"
        finally:
            await executor.cleanup_jif_subscriptions(ctx.job_id)


@pytest.mark.asyncio
async def test_dry_run_skips_subscription():
    # is_dry_run is a derived property from context_params
    ctx = ExecutionContext(
        job_id=f"job-{time.time_ns()}",
        workflow_id="wf-jif-dry-run",
        context_params={"dry_run": True},
    )

    executor = MarketStatusNodeExecutor()
    # dry_run 에서는 broker_connection 없이도 즉시 반환
    result = await executor.execute(
        node_id="ms1",
        node_type="MarketStatusNode",
        config={},
        context=ctx,
    )
    assert result["dry_run"] is True
    assert result["status"] == "skipped_dry_run"


@pytest.mark.asyncio
async def test_missing_broker_connection_raises():
    from programgarden_core.exceptions import ConnectionError as PGConnectionError

    ctx = _build_context()
    executor = MarketStatusNodeExecutor()

    with pytest.raises(PGConnectionError, match="BrokerNode 연결이 필요합니다"):
        await executor.execute(
            node_id="ms1",
            node_type="MarketStatusNode",
            config={},  # connection 없음 + DAG 조상도 없음
            context=ctx,
        )


@pytest.mark.asyncio
async def test_cleanup_removes_subscription():
    async with MockJIFServer(scenario_timeout) as server:
        _install_stub_ls("overseas_stock", server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": "overseas_stock",
            },
            stay_connected=True,
        )

        await executor.execute(
            node_id="ms1",
            node_type="MarketStatusNode",
            config=config,
            context=ctx,
        )
        sub_key = f"{ctx.job_id}::ms1"
        assert sub_key in MarketStatusNodeExecutor._active_subscriptions

        await executor.cleanup_jif_subscriptions(ctx.job_id)
        assert sub_key not in MarketStatusNodeExecutor._active_subscriptions


# ---------------------------------------------------------------------------
# BrokerNode 타입별 호환성 — 3종 broker 모두에서 구독 가능
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "broker_product",
    ["overseas_stock", "overseas_futures", "korea_stock"],
)
@pytest.mark.asyncio
async def test_broker_type_agnostic(broker_product: str):
    """3종 broker credential 중 어느 것과도 JIF 구독 가능."""

    async with MockJIFServer(scenario_weekday_us_open_kr_close) as server:
        _install_stub_ls(broker_product, server.wss_url)
        ctx = _build_context()
        executor = MarketStatusNodeExecutor()

        config = _make_config(
            broker_connection={
                "appkey": "stub-appkey",
                "appsecret": "stub-secret",
                "paper_trading": False,
                "product": broker_product,
            },
            stay_connected=True,
        )

        try:
            await executor.execute(
                node_id="ms1",
                node_type="MarketStatusNode",
                config=config,
                context=ctx,
            )
            ok = await _wait_until(
                lambda: ctx.get_market_status("US") is not None, timeout=3.0
            )
            assert ok, f"{broker_product} broker 로 JIF 구독 실패"

            # 해외선물 broker 이더라도 statuses 에는 해외선물 시장 없음
            statuses = ctx.get_all_market_statuses()
            overseas_futures_keys = {"CME", "HKEX_FUTURES", "SGX_FUTURES"}
            assert not (
                overseas_futures_keys & set(statuses.keys())
            ), f"해외선물 시장은 JIF 범위 밖: {statuses.keys()}"
        finally:
            await executor.cleanup_jif_subscriptions(ctx.job_id)

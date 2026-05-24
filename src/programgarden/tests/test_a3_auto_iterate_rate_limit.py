"""
A-3 재현 + 수정 검증 테스트

Finding: auto-iterate 루프가 executor의 rate-limit guard를 우회하여
주문 노드의 min_interval_sec=5가 per-item 실행에 적용되지 않는다.

수정 방향 (사용자 결정): skip이 아닌 spacing — 모든 N 아이템이 실행되되
consecutive 실행 사이에 min_interval_sec 이상의 간격이 보장됨.

재현 테스트: 3종목 auto-iterate 시 min_interval_sec 간격 없이 즉시 연속 발화.
수정 검증: (a) call_count == N (모두 실행), (b) 연속 실행 간격 ≥ min_interval_sec.
테스트 속도 확보: 실제 5초 대신 0.2초짜리 작은 min_interval_sec를 monkeypatch로 주입.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from programgarden.executor import WorkflowJob
from programgarden_core.models.connection_rule import RateLimitConfig


# ---------------------------------------------------------------------------
# Minimal mock infrastructure
# ---------------------------------------------------------------------------

class _MockContext:
    """테스트용 최소 ExecutionContext"""

    def __init__(self):
        self._node_states: Dict[str, Any] = {}
        self.is_running = True
        self.logs: List[dict] = []
        self._iteration_item: Any = None
        self._iteration_index: int = 0
        self._iteration_total: int = 0

    def get_node_state(self, node_id: str, key: str) -> Any:
        return self._node_states.get(f"{node_id}:{key}")

    def set_node_state(self, node_id: str, key: str, value: Any) -> None:
        self._node_states[f"{node_id}:{key}"] = value

    def log(self, level: str, message: str, node_id: Optional[str] = None) -> None:
        self.logs.append({"level": level, "message": message, "node_id": node_id})

    async def notify_node_state(self, **kwargs) -> None:
        pass

    def set_output(self, node_id: str, port_name: str, value: Any) -> None:
        pass

    def get_all_outputs(self, node_id: str) -> dict:
        return {}

    def set_iteration_context(self, item: Any, idx: int, total: int) -> None:
        self._iteration_item = item
        self._iteration_index = idx
        self._iteration_total = total

    def clear_iteration_context(self) -> None:
        self._iteration_item = None
        self._iteration_index = 0
        self._iteration_total = 0

    def get_expression_context(self):
        """ExpressionEvaluator에 필요한 컨텍스트"""
        from programgarden.context import ExpressionContext
        ctx = ExpressionContext.__new__(ExpressionContext)
        ctx.node_outputs = {}
        ctx.context_params = {}
        ctx.iteration_item = self._iteration_item
        ctx.iteration_index = self._iteration_index
        ctx.iteration_total = self._iteration_total
        return ctx


class _TimedMockExecutor:
    """execute_node 호출 타임스탬프 기록"""

    def __init__(self):
        self.call_times: List[float] = []

    async def execute_node(self, **kwargs) -> dict:
        self.call_times.append(time.monotonic())
        return {"success": True, "order_no": "mock-order"}


class _MockWorkflow:
    pass


class _MockNode:
    def __init__(self, node_type: str):
        self.node_type = node_type
        self.plugin = None
        self.fields = {}


def _make_job(ctx=None) -> WorkflowJob:
    context = ctx or _MockContext()
    job = object.__new__(WorkflowJob)
    job.context = context
    job.executor = _TimedMockExecutor()
    job.workflow = _MockWorkflow()
    return job


# ---------------------------------------------------------------------------
# A-3 재현 테스트: 버그 — rate-limit guard 우회로 즉시 연속 발화
# ---------------------------------------------------------------------------

class TestA3Reproduction:
    """
    버그 재현: 수정 전 코드에서 3종목 auto-iterate 시
    min_interval_sec=5 간격 없이 3회 모두 즉시 연속 발화함을 증명.

    수정 후 spacing이 적용되므로 이 테스트는 xfail(strict=True).
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "A-3 수정 완료 (spacing): 3종목 auto-iterate 시 item간 sleep이 삽입되어 "
            "0.001s 이내 연속 발화가 더 이상 불가능함. "
            "TestA3SpacingFix 가 수정된 동작을 검증."
        ),
    )
    async def test_no_spacing_old_behavior_instant_fire(self):
        """
        REPRO (xfail after fix): 수정 전에는 3종목 모두 즉시 발화 (elapsed < 0.05s).

        0.2초 min_interval_sec를 monkeypatch해도 간격 없이 모두 발화하면 버그 확인.
        수정 후에는 sleep이 삽입되어 0.4초+(=2×0.2s) 이상 걸리므로 assert 실패 → xfail.
        """
        PATCHED_INTERVAL = 0.2  # 빠른 테스트용

        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )

        job = _make_job()
        node = _MockNode("OverseasStockNewOrderNode")
        items = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 100},
            {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 1, "price": 200},
            {"symbol": "NVDA", "exchange": "NASDAQ", "quantity": 1, "price": 300},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            t_start = time.monotonic()
            await job._execute_with_auto_iterate(
                node_id="order1", node=node, config={}, items=items, port_name="item",
            )
            elapsed = time.monotonic() - t_start

        call_count = len(job.executor.call_times)

        # 버그 상태 어서션 (수정 후에는 실패 → xfail):
        # 모두 발화했고 총 소요가 min_interval_sec 미만이면 spacing 미적용 증명
        assert call_count == 3, f"예상 3, 실제 {call_count}"
        assert elapsed < PATCHED_INTERVAL, (
            f"elapsed={elapsed:.3f}s — spacing이 삽입됐으므로 수정 완료 (xfail 정상)"
        )


# ---------------------------------------------------------------------------
# A-3 수정 검증: spacing — 모든 N 아이템 실행 + 간격 ≥ min_interval_sec
# ---------------------------------------------------------------------------

PATCHED_INTERVAL = 0.2  # 0.2초 — 빠른 CI/테스트용


class TestA3SpacingFix:
    """
    수정 검증:
    (a) call_count == N — 모든 아이템이 실행됨 (skip 없음)
    (b) 연속 실행 간격 ≥ min_interval_sec (spacing 보장)
    """

    @pytest.mark.asyncio
    async def test_all_items_execute_no_skip(self):
        """
        핵심 검증 (a): 3종목 모두 execute_node가 호출됨 (skip 없음).

        수정 전 skip 동작이었다면 call_count == 1. 수정 후 spacing이면 call_count == 3.
        """
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("OverseasStockNewOrderNode")
        items = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 100},
            {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 1, "price": 200},
            {"symbol": "NVDA", "exchange": "NASDAQ", "quantity": 1, "price": 300},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            await job._execute_with_auto_iterate(
                node_id="order1", node=node, config={}, items=items, port_name="item",
            )

        call_count = len(job.executor.call_times)
        assert call_count == 3, (
            f"수정 실패(skip 발생): call_count={call_count}, 예상=3. "
            "spacing 방식은 모든 아이템을 실행해야 한다 (skip 없음)."
        )
        print(f"\n  [A-3 (a)] 모든 {call_count}종목 실행 확인 — skip 없음")

    @pytest.mark.asyncio
    async def test_consecutive_spacing_gte_min_interval(self):
        """
        핵심 검증 (b): 연속 실행 간격 ≥ min_interval_sec.

        3종목 auto-iterate에서 call_times[1]-call_times[0] ≥ PATCHED_INTERVAL
        및 call_times[2]-call_times[1] ≥ PATCHED_INTERVAL 이어야 한다.
        """
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("OverseasStockNewOrderNode")
        items = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 100},
            {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 1, "price": 200},
            {"symbol": "NVDA", "exchange": "NASDAQ", "quantity": 1, "price": 300},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            await job._execute_with_auto_iterate(
                node_id="order1", node=node, config={}, items=items, port_name="item",
            )

        times = job.executor.call_times
        assert len(times) == 3, f"call_count={len(times)}, 예상=3"

        gap_1_2 = times[1] - times[0]
        gap_2_3 = times[2] - times[1]

        # 소량의 타이밍 tolerance 허용 (5% margin)
        tolerance = PATCHED_INTERVAL * 0.95

        assert gap_1_2 >= tolerance, (
            f"간격 부족: items[0]→[1] = {gap_1_2:.4f}s, "
            f"최소 {tolerance:.4f}s 필요 (min_interval_sec={PATCHED_INTERVAL})"
        )
        assert gap_2_3 >= tolerance, (
            f"간격 부족: items[1]→[2] = {gap_2_3:.4f}s, "
            f"최소 {tolerance:.4f}s 필요 (min_interval_sec={PATCHED_INTERVAL})"
        )

        print(
            f"\n  [A-3 (b)] 간격 확인: "
            f"[0→1]={gap_1_2:.4f}s, [1→2]={gap_2_3:.4f}s "
            f"(min={PATCHED_INTERVAL}s)"
        )

    @pytest.mark.asyncio
    async def test_total_elapsed_consistent_with_spacing(self):
        """
        총 소요 시간이 (N-1) × min_interval_sec 이상이어야 함.

        3종목: 총 ≥ 2 × 0.2s = 0.4s
        """
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("OverseasStockNewOrderNode")
        items = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 100},
            {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 1, "price": 200},
            {"symbol": "NVDA", "exchange": "NASDAQ", "quantity": 1, "price": 300},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            t_start = time.monotonic()
            await job._execute_with_auto_iterate(
                node_id="order1", node=node, config={}, items=items, port_name="item",
            )
            elapsed = time.monotonic() - t_start

        n_items = len(items)
        min_expected = (n_items - 1) * PATCHED_INTERVAL * 0.9  # 10% tolerance
        assert elapsed >= min_expected, (
            f"총 소요 {elapsed:.4f}s < 예상 최소 {min_expected:.4f}s "
            f"({n_items}종목 × {PATCHED_INTERVAL}s)"
        )
        print(f"\n  [A-3 총소요] {elapsed:.4f}s ≥ {min_expected:.4f}s 확인")

    @pytest.mark.asyncio
    async def test_non_order_node_no_spacing_applied(self):
        """
        하위 호환: rate-limit 없는 ConditionNode는 spacing 없이 즉시 3회 실행.
        """
        job = _make_job()
        node = _MockNode("ConditionNode")
        items = [
            {"symbol": "AAPL", "rsi": 28.5},
            {"symbol": "TSLA", "rsi": 35.0},
            {"symbol": "NVDA", "rsi": 42.0},
        ]

        t_start = time.monotonic()
        await job._execute_with_auto_iterate(
            node_id="cond1", node=node, config={}, items=items, port_name="item",
        )
        elapsed = time.monotonic() - t_start

        call_count = len(job.executor.call_times)
        assert call_count == 3, f"하위호환 실패: ConditionNode {call_count}회 (예상 3)"
        # rate-limit 없으므로 0.1s 이내에 완료되어야 함
        assert elapsed < 0.5, f"ConditionNode 소요 {elapsed:.4f}s — spacing이 잘못 적용됨"
        print(f"\n  [A-3 하위호환] ConditionNode {call_count}회, {elapsed:.4f}s — spacing 없음")

    @pytest.mark.asyncio
    async def test_first_item_executes_immediately(self):
        """
        첫 번째 아이템은 간격 없이 즉시 실행되어야 한다 (직전 실행 없음).
        """
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("OverseasStockNewOrderNode")
        items = [{"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 100}]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            t_start = time.monotonic()
            await job._execute_with_auto_iterate(
                node_id="order1", node=node, config={}, items=items, port_name="item",
            )
            elapsed = time.monotonic() - t_start

        assert len(job.executor.call_times) == 1
        # 단일 아이템: sleep 없이 즉시 실행되어야 함
        assert elapsed < PATCHED_INTERVAL * 0.5, (
            f"첫 번째 아이템에 불필요한 sleep이 삽입됨: {elapsed:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_futures_order_node_spacing_applied(self):
        """OverseasFuturesNewOrderNode도 동일한 spacing 적용."""
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("OverseasFuturesNewOrderNode")
        items = [
            {"symbol": "HSIU25", "exchange": "HKEX", "quantity": 1, "price": 20000},
            {"symbol": "ESPU25", "exchange": "CME", "quantity": 1, "price": 5000},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            await job._execute_with_auto_iterate(
                node_id="fut_order", node=node, config={}, items=items, port_name="item",
            )

        times = job.executor.call_times
        assert len(times) == 2, f"call_count={len(times)}, 예상 2"
        gap = times[1] - times[0]
        assert gap >= PATCHED_INTERVAL * 0.95, (
            f"선물 주문 간격 {gap:.4f}s < {PATCHED_INTERVAL * 0.95:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_korea_stock_order_node_spacing_applied(self):
        """KoreaStockNewOrderNode도 동일한 spacing 적용."""
        mock_rate_limit = RateLimitConfig(
            min_interval_sec=PATCHED_INTERVAL,
            max_concurrent=1,
            on_throttle="skip",
        )
        job = _make_job()
        node = _MockNode("KoreaStockNewOrderNode")
        items = [
            {"symbol": "005930", "exchange": "KRX", "quantity": 10, "price": 70000},
            {"symbol": "000660", "exchange": "KRX", "quantity": 5, "price": 160000},
        ]

        with patch(
            "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
            new=mock_rate_limit,
        ):
            await job._execute_with_auto_iterate(
                node_id="kr_order", node=node, config={}, items=items, port_name="item",
            )

        times = job.executor.call_times
        assert len(times) == 2, f"call_count={len(times)}, 예상 2"
        gap = times[1] - times[0]
        assert gap >= PATCHED_INTERVAL * 0.95, (
            f"국내주식 주문 간격 {gap:.4f}s < {PATCHED_INTERVAL * 0.95:.4f}s"
        )

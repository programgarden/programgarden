"""
dry_run 자동반복 간격 대기(pacing) 회귀 테스트 — 3.1.1

배경 (prod 대화 f2eed93c, 2026-08-28): 주문 노드는 dry_run 에서 LS 를 부르지 않고
`DRYRUN-…` 모의 응답을 돌려주는데도 auto-iterate 루프는 클래스 `_rate_limit`
(min_interval_sec=5) 을 그대로 지켜 16건 × 5초 ≈ 75초를 잠들었다. 그 시간이
빌드 도구의 60초 타임아웃을 넘겨 자동매매가 저장되지 못했다.

수정: `_auto_iterate_pacing_sleep` 이 dry_run 에서 **모의 응답으로 단락되는 노드**
(`DRY_RUN_SIMULATED_NODE_TYPES` + 메시징 카테고리)에 한해 간격 대기를 건너뛴다.
블랭킷 skip 이 아니다 — dry_run 에서도 실제 호출하는 HTTPRequestNode 는 간격 유지,
runtime 은 어떤 노드든 무변화.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import WorkflowExecutor, WorkflowJob
from programgarden_core.models.connection_rule import RateLimitConfig


# ---------------------------------------------------------------------------
# 최소 mock (tests/test_a3_auto_iterate_rate_limit.py 와 같은 모양 + dry_run 플래그)
# ---------------------------------------------------------------------------

class _MockContext:
    def __init__(self, *, dry_run: bool = False, deep_validate: bool = False):
        self._node_states: Dict[str, Any] = {}
        self.is_running = True
        self.is_dry_run = dry_run or deep_validate
        self.is_deep_validate = deep_validate
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
        from programgarden.context import ExpressionContext
        ctx = ExpressionContext.__new__(ExpressionContext)
        ctx.node_outputs = {}
        ctx.context_params = {}
        ctx.iteration_item = self._iteration_item
        ctx.iteration_index = self._iteration_index
        ctx.iteration_total = self._iteration_total
        return ctx


class _TimedMockExecutor:
    def __init__(self):
        self.call_times: List[float] = []

    async def execute_node(self, **kwargs) -> dict:
        self.call_times.append(time.monotonic())
        return {"status": "simulated", "dry_run": True}


class _MockNode:
    def __init__(self, node_type: str):
        self.node_type = node_type
        self.plugin = None
        self.fields = {}


def _make_job(ctx: _MockContext) -> WorkflowJob:
    job = object.__new__(WorkflowJob)
    job.context = ctx
    job.executor = _TimedMockExecutor()
    job.workflow = object()
    return job


def _symbols(n: int) -> List[dict]:
    return [
        {"symbol": f"SYM{i:02d}", "exchange": "NASDAQ", "quantity": 1, "price": 100 + i}
        for i in range(n)
    ]


# 테스트 속도용 간격 — 실제 5초 대신 0.2초를 주입한다. skip 이 깨지면 (N-1)×0.2 초가
# 걸려 어서션이 바로 잡는다.
INTERVAL = 0.2


# ---------------------------------------------------------------------------
# 1. 핵심 회귀: 주문 노드 16건 dry_run auto-iterate 가 간격 없이 즉시 끝난다
# ---------------------------------------------------------------------------

async def test_order_node_dry_run_16_items_no_pacing():
    ctx = _MockContext(dry_run=True)
    job = _make_job(ctx)
    node = _MockNode("OverseasStockNewOrderNode")
    items = _symbols(16)

    with patch(
        "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
        new=RateLimitConfig(min_interval_sec=INTERVAL, max_concurrent=1, on_throttle="skip"),
    ):
        t0 = time.monotonic()
        await job._execute_with_auto_iterate(
            node_id="buy_order", node=node, config={}, items=items, port_name="item",
        )
        elapsed = time.monotonic() - t0

    assert len(job.executor.call_times) == 16, "모든 아이템은 여전히 실행돼야 한다(skip 아님)"
    # 15 × 0.2 = 3.0s 가 걸리면 pacing 이 살아 있는 것. 즉시 끝나야 한다.
    assert elapsed < INTERVAL, f"dry_run 모의 주문에 pacing 이 적용됨: elapsed={elapsed:.3f}s"
    assert any("pacing skipped for simulated node" in l["message"] for l in ctx.logs)


@pytest.mark.parametrize("node_type", [
    "OverseasStockModifyOrderNode", "OverseasStockCancelOrderNode",
    "OverseasFuturesNewOrderNode", "KoreaStockNewOrderNode",
])
async def test_other_order_families_dry_run_no_pacing(node_type: str):
    """정정/취소·선물·국내 주문도 같은 집합 — 한 상품군만 고쳐지는 일이 없게."""
    ctx = _MockContext(dry_run=True)
    job = _make_job(ctx)
    items = _symbols(3)
    rl = RateLimitConfig(min_interval_sec=INTERVAL, max_concurrent=1, on_throttle="skip")
    with patch("programgarden_core.nodes.order.BaseOrderNode._rate_limit", new=rl), \
         patch("programgarden_core.nodes.order.BaseModifyOrderNode._rate_limit", new=rl):
        t0 = time.monotonic()
        await job._execute_with_auto_iterate(
            node_id="o", node=_MockNode(node_type), config={}, items=items, port_name="item",
        )
        elapsed = time.monotonic() - t0
    assert len(job.executor.call_times) == 3
    assert elapsed < INTERVAL, f"{node_type}: elapsed={elapsed:.3f}s"


# ---------------------------------------------------------------------------
# 2. 블랭킷 skip 이 아니다 — dry_run 에서도 실제 호출하는 노드는 간격 유지
# ---------------------------------------------------------------------------

async def test_http_request_node_keeps_pacing_in_dry_run():
    ctx = _MockContext(dry_run=True)
    job = _make_job(ctx)
    node = _MockNode("HTTPRequestNode")
    items = [{"url": f"https://example.invalid/{i}"} for i in range(3)]

    with patch(
        "programgarden_core.nodes.data.HTTPRequestNode._rate_limit",
        new=RateLimitConfig(min_interval_sec=INTERVAL, max_concurrent=1, on_throttle="skip"),
    ):
        t0 = time.monotonic()
        await job._execute_with_auto_iterate(
            node_id="http", node=node, config={}, items=items, port_name="item",
        )
        elapsed = time.monotonic() - t0

    assert len(job.executor.call_times) == 3
    assert elapsed >= 2 * INTERVAL * 0.9, (
        f"HTTPRequestNode 는 dry_run 에서도 실제 호출하므로 간격을 지켜야 한다: elapsed={elapsed:.3f}s"
    )


# ---------------------------------------------------------------------------
# 3. runtime 무변화 — dry_run 이 아니면 주문 노드도 종전대로 간격 유지
# ---------------------------------------------------------------------------

async def test_order_node_runtime_keeps_pacing():
    ctx = _MockContext(dry_run=False)
    job = _make_job(ctx)
    node = _MockNode("OverseasStockNewOrderNode")
    items = _symbols(3)

    with patch(
        "programgarden_core.nodes.order.BaseOrderNode._rate_limit",
        new=RateLimitConfig(min_interval_sec=INTERVAL, max_concurrent=1, on_throttle="skip"),
    ):
        t0 = time.monotonic()
        await job._execute_with_auto_iterate(
            node_id="buy_order", node=node, config={}, items=items, port_name="item",
        )
        elapsed = time.monotonic() - t0

    assert len(job.executor.call_times) == 3
    assert elapsed >= 2 * INTERVAL * 0.9, f"runtime pacing 이 사라짐: elapsed={elapsed:.3f}s"
    gaps = [b - a for a, b in zip(job.executor.call_times, job.executor.call_times[1:])]
    assert all(g >= INTERVAL * 0.9 for g in gaps), gaps


# ---------------------------------------------------------------------------
# 4. 집합 ↔ executor dry_run 분기 1:1 — 집합의 주문 타입은 정말 모의 응답으로 단락된다
# ---------------------------------------------------------------------------

def _dry_ctx() -> ExecutionContext:
    return ExecutionContext(
        job_id="pacing-set-check", workflow_id="wf", context_params={"dry_run": True},
    )


@pytest.mark.parametrize(
    "node_type",
    sorted(t for t in WorkflowJob.DRY_RUN_SIMULATED_NODE_TYPES if "Order" in t),
)
async def test_simulated_set_order_types_really_short_circuit(node_type: str):
    """집합에 적힌 주문 타입마다 등록된 executor 가 dry_run 에서 LS 호출 없이
    simulated 를 돌려준다(connection 미제공 — 실경로면 에러)."""
    ex = WorkflowExecutor()
    node_executor = ex._executors[node_type]
    result = await node_executor.execute(
        node_id="n", node_type=node_type,
        config={"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 1.0,
                "original_order_id": "X"},
        context=_dry_ctx(),
    )
    assert result.get("status") == "simulated" and result.get("dry_run") is True


async def test_simulated_set_ai_agent_short_circuits_without_llm():
    ex = WorkflowExecutor()
    result = await ex._executors["AIAgentNode"].execute(
        node_id="agent", node_type="AIAgentNode",
        config={"system_prompt": "x", "user_prompt": "y", "output_format": "text"},
        context=_dry_ctx(),
    )
    assert "response" in result


def test_messaging_category_is_simulated_via_category():
    """TelegramNode 는 집합에 없지만 category=MESSAGING 으로 판별된다(GenericNodeExecutor
    의 dry_run no-op 가드와 같은 기준)."""
    import programgarden_community  # noqa: F401 — 커뮤니티 노드 등록 (TelegramNode)
    from programgarden_core.registry import NodeTypeRegistry
    job = _make_job(_MockContext(dry_run=True))
    cls = NodeTypeRegistry().get("TelegramNode")
    assert cls is not None
    assert job._is_dry_run_simulated("TelegramNode", cls) is True
    assert job._is_dry_run_simulated("HTTPRequestNode", NodeTypeRegistry().get("HTTPRequestNode")) is False
    assert job._is_dry_run_simulated("OverseasStockHistoricalDataNode", None) is False

"""Split 분기 안 주문 노드의 node_state 관측성 (2026-08-16).

결함: 분기 노드는 메인 루프가 건너뛰고(⏭ Skipping branch node) SplitNode 의
_execute_branch_for_item 이 직접 실행하는데, 그 경로엔 notify_node_state 가 없어
분기 안에서 실주문이 나가도 리스너(트레이 per-order durable 로그·SSE)가 완료
이벤트를 전혀 받지 못했다 → order_fills 적재 0행.

수정 계약:
- 분기 노드 실행 결과에 주문 결과(order/modify/cancel_result)가 실려 있으면
  아이템마다 COMPLETED node_state 를 방출한다 (outputs 동봉).
- "제출할 주문 없음"(reason: no_signal/fetch_failed/no_symbol)은 방출하지 않는다
  — 실시간 분기의 틱 재구동마다 재발화해 이벤트 홍수가 되는 것을 막는다.
- 주문 결과가 없는 일반 분기 노드는 종전대로 미방출(전면 방출은 SplitNode
  시맨틱 개편 몫).
"""

from __future__ import annotations

import asyncio
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest


class _CaptureListener:
    """on_node_state_change 만 캡처하고 나머지 훅은 전부 no-op (Protocol 덕타이핑)."""

    def __init__(self) -> None:
        self.node_events: List[Any] = []

    async def on_node_state_change(self, event) -> None:
        self.node_events.append(event)

    def __getattr__(self, name: str):
        async def _noop(*args, **kwargs) -> None:
            return None
        return _noop


def _split_order_workflow(symbols: list[dict]) -> dict:
    return {
        "id": "wf-split-order-events",
        "name": "Split Branch Order Events",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
            {"id": "wl", "type": "WatchlistNode", "symbols": symbols},
            {"id": "split", "type": "SplitNode"},
            {
                "id": "order1",
                "type": "OverseasStockNewOrderNode",
                "side": "buy",
                "order_type": "limit",
                "order": {
                    "symbol": "{{ nodes.split.item }}",
                    "exchange": "NASDAQ",
                    "quantity": 1,
                    "price": 150.0,
                },
            },
            {"id": "agg", "type": "AggregateNode", "mode": "collect"},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "wl"},
            {"from": "wl", "to": "split"},
            {"from": "split", "to": "order1"},
            {"from": "order1", "to": "agg"},
        ],
        "credentials": [
            {
                "credential_id": "broker-cred",
                "type": "broker_ls_overseas_stock",
                "data": [
                    {"key": "appkey", "value": "test-appkey"},
                    {"key": "appsecret", "value": "test-appsecret"},
                ],
            }
        ],
    }


def _order1_events(listener: _CaptureListener) -> list:
    # 메인 루프는 분기 노드를 skip 하며 PENDING 을 방출한다(기존 동작) — 이 테스트의
    # 관심사는 분기 실행이 새로 방출하는 **COMPLETED**(주문 결과 동봉)뿐이다.
    return [
        e for e in listener.node_events
        if e.node_id == "order1" and e.state.value == "completed"
    ]


@pytest.mark.asyncio
async def test_branch_order_node_emits_completed_per_item():
    """분기 안 주문 노드: 아이템(종목)마다 COMPLETED 1회 + outputs 에 order_result."""
    from programgarden import WorkflowExecutor
    from programgarden.executor import NewOrderNodeExecutor

    async def fake_execute_overseas_stock(self_ex, ls, order, side, order_type, config, context, node_id):
        symbol = (order or {}).get("symbol") or "?"
        if isinstance(symbol, dict):  # split item(dict)이 그대로 온 경우
            symbol = symbol.get("symbol") or "?"
        return {
            "order_result": {
                "success": True,
                "symbol": symbol,
                "exchange": "NASDAQ",
                "side": "buy",
                "quantity": 1,
                "price": 150.0,
                "status": "submitted",
                "error": None,
                "diagnostics": None,
            },
            "order_id": f"ORD-{symbol}",
        }

    listener = _CaptureListener()
    workflow = _split_order_workflow(
        [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]
    )

    with patch.object(
        NewOrderNodeExecutor, "_execute_overseas_stock", new=fake_execute_overseas_stock
    ), patch("programgarden.executor.ensure_ls_login") as login_mock:
        login_mock.return_value = (MagicMock(), True, None)
        executor = WorkflowExecutor()
        job = await asyncio.wait_for(
            executor.execute(workflow, listeners=[listener]), timeout=15.0
        )
        await asyncio.wait_for(job._task, timeout=15.0)

    events = _order1_events(listener)
    assert len(events) == 2, (
        f"분기 아이템 2개 → 주문 완료 이벤트 2회 기대, 실제 {len(events)} — "
        "분기 실행 경로가 node_state 를 방출하지 않는 회귀(⏭ Skipping branch node)"
    )
    symbols = set()
    for e in events:
        assert e.state.value == "completed"
        assert isinstance(e.outputs, dict)
        result = e.outputs.get("order_result")
        assert isinstance(result, dict) and result.get("success") is True
        symbols.add(result.get("symbol"))
    assert symbols == {"AAPL", "MSFT"}, f"아이템별 결과가 아님: {symbols}"


@pytest.mark.asyncio
async def test_branch_order_nonevent_and_plain_nodes_do_not_emit():
    """no_signal 빈 결과는 미방출(틱 홍수 방지) + 주문 없는 분기 노드도 종전대로 미방출."""
    from programgarden import WorkflowExecutor
    from programgarden.executor import NewOrderNodeExecutor

    async def fake_no_signal(self_ex, ls, order, side, order_type, config, context, node_id):
        return {
            "order_result": {
                "success": False,
                "error": "No order to submit",
                "reason": "no_signal",
                "message": "no signal",
                "detail": "",
            },
            "order_id": "",
        }

    listener = _CaptureListener()
    workflow = _split_order_workflow([{"symbol": "AAPL", "exchange": "NASDAQ"}])

    with patch.object(
        NewOrderNodeExecutor, "_execute_overseas_stock", new=fake_no_signal
    ), patch("programgarden.executor.ensure_ls_login") as login_mock:
        login_mock.return_value = (MagicMock(), True, None)
        executor = WorkflowExecutor()
        job = await asyncio.wait_for(
            executor.execute(workflow, listeners=[listener]), timeout=15.0
        )
        await asyncio.wait_for(job._task, timeout=15.0)

    assert _order1_events(listener) == [], "no_signal 빈 결과가 이벤트로 새어 나옴"

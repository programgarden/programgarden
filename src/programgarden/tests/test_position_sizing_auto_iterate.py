"""
PositionSizingNode 자동반복 N² 중복(실주문 안전) 회귀 테스트 — 3.1.2

배경 (prod 대화 f2eed93c, 2026-08-28): `sizing.symbols = "{{ nodes.buy_pick.symbols }}"`
인 사이징 노드가 상류 4종목 배열 때문에 4회 반복됐고, 매 회 바인딩이 **전체 4건**으로
재평가돼 병합 symbols 가 16건 → 하류 주문 노드 16회. 같은 경로가 실전에도 그대로라
실주문 4배 중복 위험이었다.

세 겹 방어:
1. `_consumes_whole_array` — 설정 모양이 전체 바인딩이면 반복하지 않음 (`symbol: {{ item }}`
   종목별 사이징 예제는 종전대로 반복)
2. `_guard_whole_array_reevaluation` — 반복 중 `symbols` 가 전체로 재평가되면 경고,
   dry_run/deep 은 현재 아이템 1건으로 좁힘 (runtime 은 경고만)
3. `_merge_iterate_results` — `orders` 배열 병합 + (symbol, exchange) 중복 제거
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from programgarden.executor import (
    BrokerNodeExecutor,
    NewOrderNodeExecutor,
    WorkflowExecutor,
    WorkflowJob,
)

from test_dry_run_auto_iterate_pacing import _MockContext, _MockNode  # noqa: E402


SYMBOLS4 = [
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "exchange": "NASDAQ"},
]


# ---------------------------------------------------------------------------
# 1. 설정 모양 판별 — 전체 바인딩이면 반복 안 함, 아이템 바인딩이면 반복
# ---------------------------------------------------------------------------

def _job() -> WorkflowJob:
    return object.__new__(WorkflowJob)


@pytest.mark.parametrize("config", [
    {"symbols": "{{ nodes.buy_pick.symbols }}", "method": "fixed_percent"},   # 미평가 전체 바인딩
    {"symbols": list(SYMBOLS4), "method": "fixed_percent"},                  # 평가된 리스트 / 리터럴
    {"symbols": "{{ nodes.logic.passed_symbols }}", "balance": "{{ nodes.account.balance }}"},
])
def test_sizing_whole_array_binding_does_not_iterate(config):
    should, _, _ = _job()._should_auto_iterate("PositionSizingNode", list(SYMBOLS4), config)
    assert should is False


@pytest.mark.parametrize("config", [
    {"symbol": "{{ item }}", "method": "fixed_percent"},                       # 예제 16/28 모양
    {"symbols": [{"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}"}]},
    {"method": "fixed_percent"},                                               # symbols 미지정 — 종전 동작
])
def test_sizing_item_binding_still_iterates(config):
    should, port, items = _job()._should_auto_iterate("PositionSizingNode", list(SYMBOLS4), config)
    assert should is True and port == "item" and len(items) == 4


def test_legacy_call_without_config_unchanged():
    """config 를 안 주는 레거시 호출은 종전 판정 그대로."""
    should, _, _ = _job()._should_auto_iterate("PositionSizingNode", list(SYMBOLS4))
    assert should is True
    should, _, _ = _job()._should_auto_iterate("ConditionNode", list(SYMBOLS4), {"symbols": "{{ nodes.x.symbols }}"})
    assert should is True, "WHOLE_ARRAY_INPUT_PORTS 에 없는 노드는 영향 없음"


# ---------------------------------------------------------------------------
# 2. 실행 경로 전체 회귀 — 4후보 → sizing → order 에서 주문 노드 실행 **정확히 4건**
#    (runtime 모드, 브로커·주문 executor 만 패치 — 실거래 차단)
# ---------------------------------------------------------------------------

def _workflow(order_binding: str, sizing_edge: Dict[str, str]) -> Dict[str, Any]:
    return {
        "id": "wf-sizing-dup",
        "name": "sizing-dup-regression",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
            {"id": "watchlist", "type": "WatchlistNode", "symbols": list(SYMBOLS4)},
            {
                "id": "sizing", "type": "PositionSizingNode",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "method": "fixed_quantity", "fixed_quantity": 1,
                # 사이징은 가격이 있어야 주문을 만든다 — 시세 노드 대신 리터럴로 공급
                "price_data": {s["symbol"]: 100.0 + i for i, s in enumerate(SYMBOLS4)},
            },
            {
                "id": "buy_order", "type": "OverseasStockNewOrderNode",
                "side": "buy", "order_type": "market", "order": order_binding,
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "sizing"},
            sizing_edge,
            {"from": "broker", "to": "buy_order"},
        ],
        "credentials": [{
            "credential_id": "broker_cred", "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "dummy", "type": "password"},
                {"key": "appsecret", "value": "dummy", "type": "password"},
            ],
        }],
    }


async def _run_counting_orders(workflow: Dict[str, Any]) -> tuple:
    calls: List[Dict[str, Any]] = []

    async def fake_broker(self, node_id, node_type, config, context, **kw):
        return {"connection": {"product": "overseas_stock", "paper_trading": True,
                               "credential_id": "broker_cred", "appkey": "x", "appsecret": "y"}}

    async def fake_order(self, node_id, node_type, config, context, **kw):
        calls.append({"node_id": node_id, "order": config.get("order")})
        return {"order_id": f"FAKE-{len(calls)}", "status": "accepted"}

    with patch.object(BrokerNodeExecutor, "execute", new=fake_broker), \
         patch.object(NewOrderNodeExecutor, "execute", new=fake_order):
        ex = WorkflowExecutor()
        job = await ex.execute(workflow)
        try:
            await asyncio.wait_for(job._task, timeout=30)
        except asyncio.TimeoutError:
            await job.stop()
    return job, calls


async def test_incident_shape_orders_exactly_four():
    """사건 DSL 모양: sizing.symbols 전체 바인딩 + sizing.orders → order({{ item }})."""
    job, calls = await _run_counting_orders(
        _workflow("{{ item }}", {"from": "sizing.orders", "to": "buy_order"})
    )
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert job.context.get_output("sizing", "symbols") is not None
    assert len(job.context.get_output("sizing", "symbols")) == 4, "symbols 가 N² 로 불어남"
    assert len(job.context.get_output("sizing", "orders")) == 4
    assert len(calls) == 4, f"주문 노드가 {len(calls)}회 실행됨 (기대 4)"
    assert sorted(c["order"]["symbol"] for c in calls) == ["AAPL", "AMZN", "MSFT", "NVDA"]


async def test_example94_shape_order_node_runs_four_times():
    """예제 94 모양: sizing → order 엣지(포트 없음) + order: {{ nodes.sizing.order }}."""
    job, calls = await _run_counting_orders(
        _workflow("{{ nodes.sizing.order }}", {"from": "sizing", "to": "buy_order"})
    )
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert len(job.context.get_output("sizing", "symbols")) == 4
    assert len(calls) == 4, f"주문 노드가 {len(calls)}회 실행됨 (기대 4, 사건 당시 16)"


async def test_per_item_sizing_shape_still_iterates_and_keeps_all_orders():
    """예제 16/28 모양(symbol: {{ item }}) 은 종전대로 종목별 반복 — 그리고 병합된 orders 가
    마지막 1건이 아니라 전부 남는다(merge 수정)."""
    wf = _workflow("{{ item }}", {"from": "sizing.orders", "to": "buy_order"})
    sizing = next(n for n in wf["nodes"] if n["id"] == "sizing")
    sizing.pop("symbols")
    sizing["symbol"] = "{{ item }}"
    job, calls = await _run_counting_orders(wf)
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert len(job.context.get_output("sizing", "symbols")) == 4
    assert len(job.context.get_output("sizing", "orders")) == 4
    assert len(calls) == 4


# ---------------------------------------------------------------------------
# 3. 방어선 2 — 반복 중 전체 배열 재평가: 경고 + dry_run 은 1건으로 좁힘, runtime 은 경고만
# ---------------------------------------------------------------------------

class _RecordingExecutor:
    def __init__(self):
        self.seen: List[int] = []

    async def execute_node(self, **kwargs) -> dict:
        syms = kwargs["config"].get("symbols")
        self.seen.append(len(syms) if isinstance(syms, list) else -1)
        return {"orders": [{"symbol": s["symbol"], "exchange": s["exchange"], "quantity": 1}
                           for s in (syms or [])],
                "symbols": syms}


async def _iterate_with_full_reeval(*, dry_run: bool):
    ctx = _MockContext(dry_run=dry_run)
    job = object.__new__(WorkflowJob)
    job.context = ctx
    job.executor = _RecordingExecutor()
    job.workflow = object()
    merged = await job._execute_with_auto_iterate(
        node_id="sizing", node=_MockNode("PositionSizingNode"),
        config={"symbols": list(SYMBOLS4)},   # 매 회 전체 4건으로 "재평가"된 것과 동일
        items=list(SYMBOLS4), port_name="item",
    )
    return ctx, job, merged


async def test_guard_narrows_to_current_item_in_dry_run():
    ctx, job, merged = await _iterate_with_full_reeval(dry_run=True)
    assert job.executor.seen == [1, 1, 1, 1]
    assert len(merged["symbols"]) == 4 and len(merged["orders"]) == 4
    warns = [l for l in ctx.logs if l["level"] == "warning" and "전체 배열" in l["message"]]
    assert len(warns) == 4


async def test_guard_only_warns_in_runtime_but_merge_dedups_orders():
    ctx, job, merged = await _iterate_with_full_reeval(dry_run=False)
    assert job.executor.seen == [4, 4, 4, 4], "runtime 은 좁히지 않는다(경고만)"
    warns = [l for l in ctx.logs if l["level"] == "warning" and "전체 배열" in l["message"]]
    assert len(warns) == 4
    # symbols 는 종전대로 16 이지만(경고 대상), orders 는 (symbol, exchange) 중복 제거로 4
    assert len(merged["symbols"]) == 16
    assert len(merged["orders"]) == 4


# ---------------------------------------------------------------------------
# 4. 병합 — orders 배열 병합 + 중복 제거, 다른 배열 필드는 무변화
# ---------------------------------------------------------------------------

def test_merge_orders_array_and_dedup():
    job = object.__new__(WorkflowJob)
    a = {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1}
    b = {"symbol": "MSFT", "exchange": "NASDAQ", "quantity": 2}
    merged = job._merge_iterate_results([
        {"orders": [a], "symbols": [a], "order": a, "total_amount": 1},
        {"orders": [a, b], "symbols": [a, b], "order": a, "total_amount": 3},
        {"orders": [b], "symbols": [b], "order": b, "total_amount": 2},
    ])
    assert merged["orders"] == [a, b]
    assert merged["symbols"] == [a, a, b, b], "symbols 는 종전 정책(중복 제거 안 함)"
    assert merged["order"] == b and merged["total_amount"] == 2, "단일 필드는 마지막 값"

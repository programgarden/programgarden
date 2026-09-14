"""조건 노드 하류의 반복 대상은 `passed_symbols` 다 — 2026-09-14 prod 손절 사고 회귀.

무엇이 깨져 있었나
------------------
prod 공유 전략(해외주식 골든크로스 + 손절 -8%)이 9/11 부터 한 번도 주문을 못 냈다.
보유 NIO 2주(-10.5%) · MARA 1주(+1.4%) · ZOMDF 1주(-30.8%) 인데도 **증권사 주문내역
0건**. 파드 로그에는 조건 노드 완료 → "Auto-iterate: sell_order - 3 items" →
[1/3] NIO [2/3] MARA [3/3] ZOMDF → 완료만 남고 주문 결과는 0줄이었다.

원인은 auto-iterate 소스 우선순위였다. ConditionNode 는 통과 여부와 무관하게
``symbols``(**평가 대상 전체**의 종목코드 **문자열** 배열)를 함께 내보내는데, 종전
우선순위(명시 from_port > symbols > 첫 출력)가 ``passed_symbols``(통과 종목 dict)보다
그 ``symbols`` 를 먼저 집었다. 그래서 매도 노드가 문자열 3개를 순회했고
``{{ item.symbol }}`` / ``{{ item.exchange }}`` / ``{{ item.quantity }}`` 가 전부 None
으로 풀려 주문을 만들지 못한 채 조용히 끝났다.

🔴 위험한 쌍둥이: 항목이 문자열이라 "아무 일도 안 일어난" 것이지 안전한 게 아니다.
   dict 였다면 **손절에 걸리지 않은 MARA 까지 전량 매도**됐다. 그래서 통과 0건이면
   ``symbols`` 로 흘러내리지 않고 아무것도 하지 않아야 한다.

⚠️ 고치는 쪽도 위험하다 — 이 파일은 "고치다가 새로 깨는 것" 도 같이 고정한다:
   ``passed_symbols`` 를 **엣지를 가로질러** 최우선으로 올리면
   (가) 출하 예제 47/48 처럼 조건 노드가 게이트로만 붙은 노드가 진짜 반복 소스(시계열)를
       잃고,
   (나) ``symbols`` 포트가 없는 LogicNode 하류가 1회 → N회로 바뀌어 **같은 주문이 N번**
       나간다.
   그래서 승격은 "선택된 소스 노드 안에서" 만 한다.

여기서 고정하는 것
------------------
1. 조건 0건 통과 → 주문 노드가 한 번도 실행되지 않는다(브로커 호출 0), 명시 배선·리터럴
   주문도 마찬가지.
2. 조건 2/3 통과 → 통과한 2건만 반복되고 미통과 1건은 주문되지 않는다. (사고의 핵심)
3. 반복 항목이 문자열/None 이면 주문을 만들지 않고 사유(어느 필드가 왜 비었는지 + 항목
   모양)를 로그·노드출력·알림에 남긴다.
4. 명시 from_port 배선은 종전대로 최우선.
5. Watchlist / SymbolFilter / Historical / LogicNode / 예제 47·48 배선은 무변화.
6. 정상 무신호·상류 조회 실패의 분류(no_signal / fetch_failed)는 진단이 가로채지 않는다.
7. 스킵된 노드도 선언된 출력 포트를 그대로(빈 값으로) 내보낸다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from programgarden.executor import (
    BrokerNodeExecutor,
    EmptyOrderReason,
    NewOrderNodeExecutor,
    WorkflowExecutor,
    WorkflowJob,
    _order_failure_from_outputs,
)


# 사고 당시 실제 보유 잔고 (손절 -8% 기준: NIO/ZOMDF 통과, MARA 미통과)
POSITIONS = [
    {"symbol": "NIO", "exchange": "NYSE", "pnl_rate": -10.5, "qty": 2, "market_code": "82"},
    {"symbol": "MARA", "exchange": "NASDAQ", "pnl_rate": 1.4, "qty": 1, "market_code": "82"},
    {"symbol": "ZOMDF", "exchange": "NASDAQ", "pnl_rate": -30.8, "qty": 1, "market_code": "82"},
]

# 전 종목이 손절선 위 — 통과 0건
POSITIONS_ALL_SAFE = [{**p, "pnl_rate": 5.0} for p in POSITIONS]

# 사고 DSL 의 매도 주문 배선 그대로 (from_port 없음 + `{{ item.* }}` 아이템 바인딩)
SELL_ORDER_BINDING = {
    "symbol": "{{ item.symbol }}",
    "exchange": "{{ item.exchange }}",
    "quantity": "{{ item.quantity }}",
}

# 아이템 바인딩을 **안 쓰는** 주문 설정 — "조건 통과하면 NIO 2주 매도" 류의 흔한 AI 생성 DSL.
LITERAL_ORDER = {"symbol": "NIO", "exchange": "NYSE", "quantity": 2}

BROKER_CREDENTIALS = [{
    "credential_id": "broker_cred", "type": "broker_ls_overseas_stock",
    "data": [
        {"key": "appkey", "value": "dummy", "type": "password"},
        {"key": "appsecret", "value": "dummy", "type": "password"},
    ],
}]


def _workflow(
    positions: List[Dict[str, Any]],
    *,
    from_port: str = "",
    order: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    edge = {"from": f"stop_cond.{from_port}" if from_port else "stop_cond", "to": "sell_order"}
    return {
        "id": "wf-stop-loss-iteration",
        "name": "stop-loss-passed-symbols-regression",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
            {
                "id": "stop_cond", "type": "ConditionNode", "plugin": "StopLoss",
                "positions": list(positions), "fields": {"stop_loss_pct": 8},
            },
            {
                "id": "sell_order", "type": "OverseasStockNewOrderNode",
                "side": "sell", "order_type": "market",
                "order": dict(order if order is not None else SELL_ORDER_BINDING),
                "resilience": {"fallback": {"mode": "skip"}},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "stop_cond"},
            edge,
            {"from": "broker", "to": "sell_order"},
        ],
        "credentials": list(BROKER_CREDENTIALS),
    }


async def _run_counting_orders(workflow: Dict[str, Any]) -> tuple:
    """주문 executor 를 가짜로 바꿔 **실행 횟수와 주문 내용**을 센다(실거래 차단)."""
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
            # 🔴 삼키면 "주문 0건" 단언이 '워크플로우가 죽어서 0건' 인 경우에도 초록이 된다.
            pytest.fail("workflow did not finish in 30s — 'calls == []' 를 신뢰할 수 없다")
    return job, calls


# ---------------------------------------------------------------------------
# ① 통과 0건 → 주문 노드가 한 번도 실행되지 않는다
# ---------------------------------------------------------------------------

async def test_zero_passed_symbols_never_runs_the_order_node():
    job, calls = await _run_counting_orders(_workflow(POSITIONS_ALL_SAFE))

    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert job.context.get_output("stop_cond", "passed_symbols") == []
    # 조건 노드의 symbols 는 **비어 있지 않다** — 여기로 흘러내리면 전량 매도가 된다.
    assert job.context.get_output("stop_cond", "symbols") == ["NIO", "MARA", "ZOMDF"]
    assert calls == [], f"통과 0건인데 주문 노드가 {len(calls)}회 실행됐다"

    out = job.context.get_all_outputs("sell_order")
    assert out, "주문 노드가 처리되지 않았다 (워크플로우가 도중에 멈춘 것과 구분해야 한다)"
    assert out.get("reason") == "no_signal"
    assert out.get("skipped_by") == "no_upstream_signal"
    assert out.get("skipped_source_node_id") == "stop_cond", "어느 상류가 0건인지가 안 남았다"
    # resilience 의 fallback skip(`_skipped`) 과는 다른 사건이다 — 키가 겹치면 안 된다.
    assert "_skipped" not in out

    # 🔴 원장/UI/챗봇이 읽는 `result` 행은 실행하든 안 하든 **1건** 이어야 한다
    #    (`NewOrderNodeExecutor.execute` 의 불변식 — tests/test_order_result_port.py).
    rows = out.get("result")
    assert isinstance(rows, list) and len(rows) == 1, f"result 행이 {rows}"
    assert rows[0]["reason"] == "no_signal"
    assert rows[0]["skipped_by"] == "no_upstream_signal"
    assert rows[0]["order_id"] == ""
    # 정상 무신호이므로 노드 실패로 승격되지 않는다.
    assert _order_failure_from_outputs(out) is None


async def test_zero_passed_symbols_skips_even_a_literal_order_node():
    """🔴 리터럴 주문이라 `{{ item }}` 이 없어도 건너뛴다 — 아니면 **미통과 종목에 실주문**이다."""
    job, calls = await _run_counting_orders(
        _workflow(POSITIONS_ALL_SAFE, order=LITERAL_ORDER)
    )
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert calls == [], f"통과 0건인데 리터럴 주문이 {len(calls)}회 나갔다"


async def test_zero_passed_symbols_skips_even_with_explicit_from_port():
    """명시 배선(`stop_cond.passed_symbols -> sell_order`)도 0건이면 실행되지 않는다."""
    job, calls = await _run_counting_orders(
        _workflow(POSITIONS_ALL_SAFE, from_port="passed_symbols", order=LITERAL_ORDER)
    )
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert calls == [], f"명시 배선 0건인데 주문이 {len(calls)}회 나갔다"


# ---------------------------------------------------------------------------
# ② 통과 2/3 → 통과한 2건만 주문, 미통과 1건은 절대 주문되지 않는다 (사고의 핵심)
# ---------------------------------------------------------------------------

async def test_only_passed_symbols_are_ordered_never_the_failed_one():
    job, calls = await _run_counting_orders(_workflow(POSITIONS))

    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    ordered = sorted(c["order"]["symbol"] for c in calls)
    assert ordered == ["NIO", "ZOMDF"], f"주문된 종목: {ordered}"
    assert "MARA" not in ordered, "손절에 걸리지 않은 종목이 매도됐다 (과매도)"

    by_symbol = {c["order"]["symbol"]: c["order"] for c in calls}
    # 문자열 순회였다면 여기가 전부 None 이었다 (사고 당시 증권사 주문내역 0건).
    assert by_symbol["NIO"]["exchange"] == "NYSE"
    assert int(by_symbol["NIO"]["quantity"]) == 2
    assert by_symbol["ZOMDF"]["exchange"] == "NASDAQ"
    assert int(by_symbol["ZOMDF"]["quantity"]) == 1


# ---------------------------------------------------------------------------
# ④ 명시 from_port 배선은 종전대로 최우선 (passed_symbols 보다도 앞선다)
# ---------------------------------------------------------------------------

async def test_explicit_from_port_still_wins_over_passed_symbols():
    job, calls = await _run_counting_orders(_workflow(POSITIONS, from_port="failed_symbols"))

    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert sorted(c["order"]["symbol"] for c in calls) == ["MARA"], \
        "명시 from_port(failed_symbols) 가 무시됐다"


# ---------------------------------------------------------------------------
# 게이트로만 붙은 조건 노드는 하류를 침묵시키지 않는다 (과잉 스킵 방지)
# ---------------------------------------------------------------------------

async def test_zero_pass_condition_does_not_silence_a_non_item_downstream_node():
    """0건 통과여도 `{{ item.* }}` 을 안 쓰는 비주문 노드는 그대로 실행되고 출력이 남는다.

    "통과 0건이면 아무것도 안 하는 게 정답" 은 **주문 노드** 이야기다. 조건 결과를
    집계·표시·전달하는 노드까지 침묵시키면 "조용히 끝내지 마라"(요구사항 4)와 어긋난다.
    """
    workflow = {
        "id": "wf-gate-only", "name": "gate-only-downstream", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
            {"id": "stop_cond", "type": "ConditionNode", "plugin": "StopLoss",
             "positions": list(POSITIONS_ALL_SAFE), "fields": {"stop_loss_pct": 8}},
            {"id": "gate", "type": "LogicNode", "operator": "any", "conditions": [
                {"is_condition_met": "{{ nodes.stop_cond.result }}",
                 "passed_symbols": "{{ nodes.stop_cond.passed_symbols }}"},
                {"is_condition_met": "{{ nodes.stop_cond.is_condition_met }}",
                 "passed_symbols": "{{ nodes.stop_cond.passed_symbols }}"},
            ]},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "stop_cond"},
            {"from": "stop_cond", "to": "gate"},
        ],
        "credentials": list(BROKER_CREDENTIALS),
    }
    job, calls = await _run_counting_orders(workflow)

    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    out = job.context.get_all_outputs("gate")
    assert out.get("skipped_by") != "no_upstream_signal", "게이트 하류가 통째로 침묵했다"
    assert out.get("passed_symbols") == []
    assert out.get("result") is False


# ---------------------------------------------------------------------------
# 소스 선택 우선순위 단위 검증 — ⑤ 다른 상류는 무변화
# ---------------------------------------------------------------------------

class _Edge:
    def __init__(self, from_node_id, to_node_id, from_port=None):
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.from_port = from_port


class _Node:
    def __init__(self, node_type):
        self.node_type = node_type


class _Workflow:
    def __init__(self, edges, nodes):
        self.edges = edges
        self.nodes = nodes


class _Ctx:
    def __init__(self, outputs: Dict[str, Dict[str, Any]]):
        self._outputs = outputs

    def get_output(self, node_id, port=None):
        node = self._outputs.get(node_id) or {}
        if port is not None:
            return node.get(port)
        return next(iter(node.values()), None) if node else None


def _job(outputs, edges, nodes=None) -> WorkflowJob:
    job = object.__new__(WorkflowJob)
    job.context = _Ctx(outputs)
    job.workflow = _Workflow(edges, nodes or {})
    return job


CONDITION_OUTPUT_2_OF_3 = {
    "symbols": ["NIO", "MARA", "ZOMDF"],
    "result": True,
    "is_condition_met": True,
    "passed_symbols": [{"symbol": "NIO", "exchange": "NYSE", "quantity": 2}],
    "failed_symbols": [{"symbol": "MARA", "exchange": "NASDAQ", "quantity": 1}],
    "symbol_results": [],
    "values": [],
}


def test_passed_symbols_beats_symbols():
    job = _job({"cond": CONDITION_OUTPUT_2_OF_3}, [_Edge("cond", "order")])
    data, source, source_node = job._select_auto_iterate_source("order")
    assert source == WorkflowJob.ITERATE_SOURCE_PASSED_SYMBOLS
    assert source_node == "cond"
    assert data == CONDITION_OUTPUT_2_OF_3["passed_symbols"]


def test_empty_passed_symbols_does_not_fall_through_to_symbols():
    """🔴 위험한 쌍둥이 — 여기서 symbols 로 흘러내리면 미통과 종목까지 전량 매도된다."""
    outputs = {"cond": {**CONDITION_OUTPUT_2_OF_3, "passed_symbols": []}}
    job = _job(outputs, [_Edge("cond", "order")])
    data, source, _ = job._select_auto_iterate_source("order")
    assert source == WorkflowJob.ITERATE_SOURCE_PASSED_SYMBOLS
    assert data == []


def test_watchlist_symbols_source_unchanged():
    outputs = {"watchlist": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"},
                                         {"symbol": "TSLA", "exchange": "NASDAQ"}]}}
    job = _job(outputs, [_Edge("watchlist", "hist")], {"watchlist": _Node("WatchlistNode")})
    data, source, _ = job._select_auto_iterate_source("hist")
    assert source == WorkflowJob.ITERATE_SOURCE_SYMBOLS
    assert [d["symbol"] for d in data] == ["AAPL", "TSLA"]


def test_symbol_filter_symbols_source_unchanged():
    outputs = {"filter": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}}
    job = _job(outputs, [_Edge("filter", "sizing")], {"filter": _Node("SymbolFilterNode")})
    data, source, _ = job._select_auto_iterate_source("sizing")
    assert source == WorkflowJob.ITERATE_SOURCE_SYMBOLS
    assert data == outputs["filter"]["symbols"]


def test_historical_merged_string_symbols_still_fall_back_to_value():
    outputs = {"hist": {
        "value": [{"symbol": "AAPL", "time_series": []}, {"symbol": "TSLA", "time_series": []}],
        "symbols": ["AAPL", "TSLA"],
    }}
    job = _job(outputs, [_Edge("hist", "cond")], {"hist": _Node("HistoricalDataNode")})
    data, source, _ = job._select_auto_iterate_source("cond")
    assert source == WorkflowJob.ITERATE_SOURCE_SYMBOLS
    assert data == outputs["hist"]["value"], "string symbols → value 폴백이 깨졌다"


def test_condition_gate_does_not_steal_the_real_iteration_source():
    """출하 예제 47/48 배선 — `hist -> touch_check` 와 `sr_detect(Condition) -> touch_check`.

    반복해야 할 것은 hist 의 시계열이다. passed_symbols 를 **엣지를 가로질러** 최우선으로
    올리면 여기서 조건 노드의 통과 목록을 순회해 `items.from` 이 0행이 되고 전략이 통째로
    신호 0 이 된다(조용한 거래 중단).
    """
    outputs = {
        "hist": {"value": [{"symbol": "AAPL", "time_series": [{"close": 1}]}],
                 "symbols": ["AAPL"]},
        "sr_detect": {**CONDITION_OUTPUT_2_OF_3, "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
    }
    job = _job(
        outputs,
        [_Edge("hist", "touch_check"), _Edge("sr_detect", "touch_check")],
        {"hist": _Node("HistoricalDataNode"), "sr_detect": _Node("ConditionNode")},
    )
    data, source, source_node = job._select_auto_iterate_source("touch_check")
    assert source == WorkflowJob.ITERATE_SOURCE_SYMBOLS
    assert source_node == "hist"
    assert data == outputs["hist"]["value"], "조건 게이트가 진짜 반복 소스를 가로챘다"


def test_logic_node_downstream_is_still_not_iterated():
    """🔴 LogicNode 는 `symbols` 포트가 없다 — 종전대로 반복이 걸리지 않아야 한다.

    passed_symbols 를 무조건 먼저 집으면 `logic -> order`(from_port 없음, 리터럴 주문)
    배선이 1회 → N회가 되어 **같은 주문이 N번** 브로커로 나간다
    (`enable_order_idempotency` 는 기본 False 라 막아 주지 못한다).
    """
    outputs = {"logic": {
        "result": True,
        "passed_symbols": [{"symbol": s, "exchange": "NASDAQ"} for s in ("A", "B", "C")],
        "details": [],
    }}
    job = _job(outputs, [_Edge("logic", "order")], {"logic": _Node("LogicNode")})
    data, source, _ = job._select_auto_iterate_source("order")
    assert source == WorkflowJob.ITERATE_SOURCE_FALLBACK
    assert data is True
    should, _port, _items = job._should_auto_iterate(
        "OverseasStockNewOrderNode", data, {"order": dict(LITERAL_ORDER)},
    )
    assert should is False, "LogicNode 하류가 종목 수만큼 반복된다 (중복 주문 경로)"


def test_account_node_is_still_not_an_iteration_fallback_source():
    outputs = {"account": {"positions": [{"symbol": "AUID", "qty": 3}]}}
    job = _job(outputs, [_Edge("account", "sizing")],
               {"account": _Node("OverseasStockAccountNode")})
    data, source, _ = job._select_auto_iterate_source("sizing")
    assert data is None and source == WorkflowJob.ITERATE_SOURCE_NONE


def test_explicit_from_port_beats_passed_symbols_unit():
    job = _job({"cond": CONDITION_OUTPUT_2_OF_3},
               [_Edge("cond", "order", from_port="failed_symbols")])
    data, source, _ = job._select_auto_iterate_source("order")
    assert source == WorkflowJob.ITERATE_SOURCE_EXPLICIT
    assert data == CONDITION_OUTPUT_2_OF_3["failed_symbols"]


def test_explicit_passed_symbols_port_is_labelled_as_a_condition_gate():
    """명시 배선이어도 `passed_symbols` 를 가리키면 0건 스킵 판정이 걸려야 한다."""
    outputs = {"cond": {**CONDITION_OUTPUT_2_OF_3, "passed_symbols": []}}
    job = _job(outputs, [_Edge("cond", "order", from_port="passed_symbols")])
    data, source, _ = job._select_auto_iterate_source("order")
    assert source == WorkflowJob.ITERATE_SOURCE_PASSED_SYMBOLS
    assert data == []


# ---------------------------------------------------------------------------
# ⑦ 스킵된 노드도 선언된 출력 포트를 그대로(빈 값으로) 내보낸다
# ---------------------------------------------------------------------------

def test_skip_outputs_keep_the_declared_port_shape():
    job = object.__new__(WorkflowJob)

    cond = job._no_signal_skip_outputs("ConditionNode", "detail", "stop_cond")
    # ConditionNode 선언 포트가 전부 있어야 한다 — 사라지면 하류 LogicNode 가
    # 이 조건을 'boolean-gate' 로 재분류하고 IfNode 비교가 깨진다.
    for port in ("result", "is_condition_met", "symbols", "passed_symbols",
                 "failed_symbols", "symbol_results", "values"):
        assert port in cond, f"{port} 포트가 사라졌다"
    assert cond["result"] is False, "boolean 포트가 배열로 바뀌었다"
    assert cond["passed_symbols"] == [] and cond["symbols"] == []
    assert cond["skipped_by"] == "no_upstream_signal"

    order = job._no_signal_skip_outputs("OverseasStockNewOrderNode", "detail", "stop_cond")
    assert isinstance(order["result"], list) and len(order["result"]) == 1
    assert order["order_result"]["reason"] == EmptyOrderReason.NO_SIGNAL.value
    assert order["order_id"] == ""


# ---------------------------------------------------------------------------
# ③ 반복 항목이 문자열/None 이면 주문을 만들지 않고 사유를 남긴다 (조용한 건너뜀 제거)
# ---------------------------------------------------------------------------

def _order_context(tmp_path, *, item: Any = None, iterating: bool = True):
    from programgarden.context import ExecutionContext

    ctx = ExecutionContext(job_id="j", workflow_id="wf", storage_dir=str(tmp_path))
    if iterating:
        ctx.set_iteration_context(item, 0, 3)
    return ctx


def _no_broker(monkeypatch, message="입력이 안 채워졌는데 브로커 로그인까지 갔다"):
    def no_login(*args, **kwargs):
        pytest.fail(message)

    monkeypatch.setattr("programgarden.executor.ensure_ls_login", no_login)


@pytest.mark.parametrize("node_type,connection", [
    ("OverseasStockNewOrderNode", {"product": "overseas_stock", "paper_trading": True}),
    ("KoreaStockNewOrderNode", {"product": "korea_stock", "paper_trading": False}),
    ("OverseasFuturesNewOrderNode", {"product": "overseas_futures", "paper_trading": True}),
])
async def test_string_iteration_item_reports_instead_of_silently_skipping(
    tmp_path, node_type, connection, monkeypatch,
):
    """문자열 항목(`{{ item.symbol }}` → None)은 주문이 되지 않고 사유가 남는다.

    바인딩은 **실제 리졸버**를 태운다(`execute` 안의 `evaluate_all_bindings`) — 해석 결과를
    손으로 적어 넣으면 표현식 엔진이 미해결 바인딩을 리터럴로 남기도록 바뀌었을 때
    이 회귀를 놓친다.
    """
    from programgarden_core.bases.listener import (
        NotificationCategory, NotificationSeverity,
    )

    _no_broker(monkeypatch)

    notifications: List[Dict[str, Any]] = []
    ctx = _order_context(tmp_path, item="NIO")

    async def capture(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(ctx, "send_notification", capture)

    out = await NewOrderNodeExecutor().execute(
        "sell_order", node_type,
        {
            "connection": dict(connection),
            "side": "sell", "order_type": "market",
            # 문자열 항목에는 속성이 없어 바인딩이 None 으로 풀린다 (리졸버가 판단한다).
            "order": dict(SELL_ORDER_BINDING),
        },
        ctx,
    )

    inner = out["order_result"]
    assert inner["success"] is False
    assert inner["reason"] == EmptyOrderReason.NO_SYMBOL.value
    assert inner["skipped_by"] == "unresolved_order_input"
    assert "symbol" in inner["unfilled_fields"] and "quantity" in inner["unfilled_fields"]
    # 국내주식은 거래소를 쓰지 않는다 — 필수로 세면 틀린 안내가 나간다.
    if "KoreaStock" in node_type:
        assert "exchange" not in inner["unfilled_fields"]
    else:
        assert "exchange" in inner["unfilled_fields"]
    assert "str" in inner["item_shape"] and "NIO" in inner["item_shape"]
    assert "passed_symbols" in inner["message_ko"], "무엇을 고쳐야 하는지가 문구에 없다"

    # 병합에서 살아남는 배열 포트 + 노드 실패 승격
    assert len(out["blocked_orders"]) == 1
    assert out["blocked_orders"][0]["reason"] == "unresolved_order_input"
    failure = _order_failure_from_outputs(out)
    assert failure and "주문 입력이 채워지지 않아" in failure, \
        "노드 상태 error 문자열에 한국어 사유가 안 실렸다"

    # 로그(경고 이상)
    warnings = [log for log in ctx.get_logs()
                if log["level"] in ("warning", "error") and log.get("node_id") == "sell_order"]
    assert warnings, "입력 미해결이 로그에 남지 않았다"
    assert any("종목코드(symbol)" in log["message"] for log in warnings)

    # 사용자 알림 경로 (⚠️ 실배포 소비자는 아직 없다 — executor 주석 참조)
    assert notifications, "사용자 알림이 발송되지 않았다"
    note = notifications[0]
    assert note["category"] == NotificationCategory.ORDER_REJECTED
    assert note["severity"] == NotificationSeverity.WARNING
    assert "passed_symbols" in note["message"]
    assert note["data"]["blocked_before_broker"] is True
    assert note["data"]["reason"] == "unresolved_order_input"


async def test_none_iteration_item_is_also_reported(tmp_path, monkeypatch):
    """반복 항목이 None 이면 '정상 무신호' 로 조용히 뭉개지 않는다."""
    _no_broker(monkeypatch)
    ctx = _order_context(tmp_path, item=None)

    out = await NewOrderNodeExecutor().execute(
        "sell_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "side": "sell", "order_type": "market", "order": dict(SELL_ORDER_BINDING)},
        ctx,
    )
    inner = out["order_result"]
    assert inner["reason"] == EmptyOrderReason.NO_SYMBOL.value
    assert inner["skipped_by"] == "unresolved_order_input"
    assert "None" in inner["item_shape"]


async def test_unresolved_template_literal_is_not_labelled_no_signal(tmp_path, monkeypatch):
    """🔴 `{{ item.symbol }}` 리터럴이 그대로 남은 것은 고장이지 '오늘 신호 없음' 이 아니다."""
    _no_broker(monkeypatch)
    # 반복 컨텍스트가 없어 표현식이 리터럴로 남는 상황을 그대로 만든다.
    ctx = _order_context(tmp_path, iterating=False)
    notifications: List[Dict[str, Any]] = []

    async def capture(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(ctx, "send_notification", capture)

    out = await NewOrderNodeExecutor().execute(
        "sell_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "side": "sell", "order_type": "market",
         "order": {"symbol": "{{ item.symbol }}", "exchange": "NASDAQ", "quantity": 3}},
        ctx,
    )
    inner = out["order_result"]
    assert inner["reason"] != EmptyOrderReason.NO_SIGNAL.value, \
        "바인딩이 깨져 주문이 못 나간 것을 '오늘 신호 없음' 으로 설명하고 있다"
    assert inner["reason"] == EmptyOrderReason.NO_SYMBOL.value
    assert inner["skipped_by"] == "unresolved_order_input"
    assert inner["unfilled_fields"] == ["symbol"]
    assert notifications, "미해석 템플릿이 조용히 끝났다"
    assert _order_failure_from_outputs(out), "노드 실패로 표면화되지 않았다"


async def test_order_binding_bound_directly_to_a_string_item(tmp_path, monkeypatch):
    """`order: {{ item }}` 로 문자열 항목을 통째로 받은 경우도 종목코드로 오해하지 않는다."""
    _no_broker(monkeypatch)
    ctx = _order_context(tmp_path, item="NIO")

    out = await NewOrderNodeExecutor().execute(
        "sell_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "side": "sell", "order_type": "market", "order": "{{ item }}"},
        ctx,
    )
    inner = out["order_result"]
    assert inner["success"] is False
    assert inner["skipped_by"] == "unresolved_order_input"
    assert "not an order object" in inner["detail"]


# ---------------------------------------------------------------------------
# ⑥ 진단이 분류를 선점하지 않는다 — 정상 무신호·상류 조회 실패 보존
# ---------------------------------------------------------------------------

async def test_normal_empty_upstream_is_still_no_signal_not_unresolved(tmp_path, monkeypatch):
    """상류가 정상적으로 빈 결과를 낸 경우는 종전대로 no_signal — 설정 누락으로 뒤바뀌지 않는다."""
    _no_broker(monkeypatch, "빈 상류 결과인데 브로커 로그인까지 갔다")
    from programgarden.context import ExecutionContext

    ctx = ExecutionContext(job_id="j", workflow_id="wf", storage_dir=str(tmp_path))
    ctx.set_output("sizing", "orders", [])
    ctx.set_output("sizing", "reason", "no_signal")

    out = await NewOrderNodeExecutor().execute(
        "buy_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "order": "{{ nodes.sizing.orders }}"},
        ctx,
    )
    assert out["order_result"]["reason"] == "no_signal"
    assert "skipped_by" not in out["order_result"]
    assert _order_failure_from_outputs(out) is None


async def test_upstream_no_signal_with_dict_order_stays_no_signal(tmp_path, monkeypatch):
    """🔴 D2 회귀 방지 — 바인딩이 None 으로 풀린 무신호 날이 매일 '주문 생성 실패' 가 되면 안 된다."""
    _no_broker(monkeypatch, "무신호 날인데 브로커 로그인까지 갔다")
    notifications: List[Dict[str, Any]] = []
    ctx = _order_context(tmp_path, iterating=False)

    async def capture(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(ctx, "send_notification", capture)

    out = await NewOrderNodeExecutor().execute(
        "buy_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         # 상류 sizing 이 orders=[] 를 내 바인딩이 전부 None 으로 풀린 모양.
         "order": {"symbol": None, "exchange": None, "quantity": None}},
        ctx,
    )
    assert out["order_result"]["reason"] == "no_signal"
    assert "skipped_by" not in out["order_result"]
    assert _order_failure_from_outputs(out) is None, "정상 무신호가 노드 실패로 승격됐다"
    assert notifications == [], "정상 무신호 날에 사용자 알림이 나갔다"
    # 진단 정보 자체는 붙여 둔다(사유를 바꾸지 않을 뿐).
    assert out["order_result"]["unfilled_fields"] == ["symbol", "exchange", "quantity"]


async def test_upstream_balance_failure_stays_fetch_failed(tmp_path, monkeypatch):
    """계좌 조회 부분 실패의 브로커 장애 원문이 '설정 누락' 으로 덮이면 안 된다."""
    _no_broker(monkeypatch, "조회 실패인데 브로커 로그인까지 갔다")
    ctx = _order_context(tmp_path, iterating=False)

    out = await NewOrderNodeExecutor().execute(
        "buy_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "balance": {"_partial_failure": True,
                     "_failure_reason": "LS balance TR failed (IGW40013)"},
         "order": {"symbol": None, "exchange": None, "quantity": None}},
        ctx,
    )
    inner = out["order_result"]
    assert inner["reason"] == EmptyOrderReason.FETCH_FAILED.value
    assert "IGW40013" in inner["detail"], "브로커 장애 원문이 사라졌다"


async def test_korea_stock_zero_quantity_is_not_promoted_to_failure(tmp_path, monkeypatch):
    """국내주식 '오늘 살 수량 0' — 거래소를 안 써도 노드 실패/알림으로 승격되지 않는다."""
    _no_broker(monkeypatch, "수량 0인데 브로커 로그인까지 갔다")
    notifications: List[Dict[str, Any]] = []
    ctx = _order_context(tmp_path, iterating=False)

    async def capture(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(ctx, "send_notification", capture)

    out = await NewOrderNodeExecutor().execute(
        "buy_order", "KoreaStockNewOrderNode",
        {"connection": {"product": "korea_stock", "paper_trading": False},
         "order": {"symbol": "005930", "quantity": 0, "price": 70000}},
        ctx,
    )
    inner = out["order_result"]
    assert inner["reason"] == EmptyOrderReason.NO_SIGNAL.value
    assert "skipped_by" not in inner
    assert inner["unfilled_fields"] == ["quantity"], "거래소가 국내주식 필수로 잡혔다"
    assert _order_failure_from_outputs(out) is None
    assert notifications == []


# ---------------------------------------------------------------------------
# 병합 생존 — 마지막 항목이 성공해도 차단된 항목이 사라지지 않는다
# ---------------------------------------------------------------------------

def test_blocked_orders_survive_auto_iterate_merge_even_when_the_last_one_succeeds():
    job = object.__new__(WorkflowJob)
    blocked = {
        "order_result": {"success": False, "reason": "no_symbol",
                         "skipped_by": "unresolved_order_input",
                         "message_ko": "주문 입력이 채워지지 않아…"},
        "order_id": "",
        "result": [],
        "blocked_orders": [{"reason": "unresolved_order_input",
                            "message_ko": "주문 입력이 채워지지 않아…"}],
    }
    ok = {
        "order_result": {"success": True, "symbol": "MARA", "status": "submitted", "error": ""},
        "order_id": "X-1",
        "result": [{"order_id": "X-1", "success": True}],
        "blocked_orders": [],
    }
    merged = job._merge_iterate_results([blocked, blocked, ok])

    assert len(merged["blocked_orders"]) == 2, "차단 항목이 병합에서 소실됐다"
    failure = _order_failure_from_outputs(merged)
    assert failure and "2건" in failure, \
        "마지막 항목이 성공하면 '3건 중 2건 차단' 이 노드 상태에서 사라진다"


def test_node_state_error_string_leads_with_the_korean_reason():
    """노드 상태 `error` 는 한국어 사유를 앞에 싣는다.

    이 문자열이 pg-worker `_broadcast('node_state')` 로 실제로 나가는 몇 안 되는
    사용자 표면이다(사용자 알림 `on_notification` 은 아직 소비자가 없다 —
    `NewOrderNodeExecutor._notify_unresolved_order_input` 주석 참조). 영어 detail 만
    가면 한국어 사용자는 무슨 일인지 알 수 없다.
    """
    outputs = {"order_result": {
        "success": False,
        "reason": EmptyOrderReason.NO_SYMBOL.value,
        "message": "No symbol provided to the order node (configuration missing).",
        "detail": "Order input was not filled in: symbol=None (missing)",
        "message_ko": "주문 입력이 채워지지 않아 주문을 만들지 않았습니다 — 문제 항목: 종목코드(symbol)=비어 있음.",
    }}
    failure = _order_failure_from_outputs(outputs)
    assert failure is not None
    assert failure.startswith("no_symbol: 주문 입력이 채워지지 않아"), failure

async def test_empty_upstream_array_is_no_signal_not_a_wiring_fault(tmp_path, monkeypatch):
    """🔴 2026-09-14 prod 실관측 — 거짓 경보 회귀 가드.

    상류(SymbolFilter)가 **정상적으로** 빈 목록을 내면(관심종목을 이미 보유 → 오늘 살 것
    없음) 반복이 일어나지 않아 `{{ item.symbol }}` 이 리터럴로 남는다. 그건 배선 고장이
    아니라 "오늘 신호 없음" 이다 — 매 실행 노드 FAILED + 알림으로 울리면 안 된다.
    (엔진 1.37.2 배포 직후 매수 노드가 10분마다 이 경보를 냈다.)
    """
    _no_broker(monkeypatch)
    ctx = _order_context(tmp_path, iterating=False)
    # 상류 리스트 포트가 **존재하고 비어 있다** — `_input_<node_id>` 의사 노드로 들어온다.
    ctx.set_output("_input_buy_order", "symbols", [])
    notifications: List[Dict[str, Any]] = []

    async def capture(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(ctx, "send_notification", capture)

    out = await NewOrderNodeExecutor().execute(
        "buy_order", "OverseasStockNewOrderNode",
        {"connection": {"product": "overseas_stock", "paper_trading": True},
         "side": "buy", "order_type": "market",
         "order": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "quantity": 1}},
        ctx,
    )
    inner = out["order_result"]
    assert inner["reason"] == EmptyOrderReason.NO_SIGNAL.value, \
        f"상류가 정상적으로 비었는데 고장으로 분류했다: {inner.get('reason')}"
    assert inner.get("skipped_by") != "unresolved_order_input"
    assert not notifications, "정상 무신호 날에 사용자 알림이 울렸다"

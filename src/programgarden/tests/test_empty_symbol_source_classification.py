"""D2 — "No symbols provided" 3분류 (AI 모델 벤치마크 2026-09-06, 서버 repo
``.claude/plans/2026-09-06-engine-defects-from-benchmark.md`` D2).

배경: 사이징/과거시세/현재가 노드가 빈 종목 목록을 받으면 종전엔 원인 불문 같은
warning("No symbols provided …")을 찍었다. 챗봇 저장 게이트(pg-ai ``_detect_input_warnings``)는
그 문구를 설계 결함으로 읽어 저장을 막으므로, ``symbols: {{ nodes.rsi.passed_symbols }}`` 로
**올바르게** 배선한 워크플로우가 모의 실행 표본에서 오늘 조건 통과 종목이 0 이라는 이유만으로
저장되지 못했다(본선 40여 건 중 대부분, 모델 무관). 수정 후:

- 바인딩/입력 포트가 있고 상류가 빈 목록을 냈다 → ``no_signal`` (info, warning 없음)
- 바인딩 표현식이 리터럴로 남았다(없는 노드/포트, 반복 밖의 ``{{ item }}``) → ``unresolved`` (warning)
- symbols/symbol 자체가 없다 → ``unbound`` (warning)
- 주문 노드는 상류 ``reason=no_signal`` 을 그대로 물려받는다(종전엔 ``no_symbol`` "설정 누락").
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from programgarden.executor import (
    EMPTY_SYMBOLS_NO_SIGNAL,
    EMPTY_SYMBOLS_UNBOUND,
    EMPTY_SYMBOLS_UNRESOLVED,
    HistoricalDataNodeExecutor,
    MarketDataNodeExecutor,
    NewOrderNodeExecutor,
    PositionSizingNodeExecutor,
    classify_empty_symbol_source,
)
from programgarden_core.models.order_diagnostics import EmptyOrderReason


class _Ctx:
    """최소 ExecutionContext — 로그 수집 + `_input_<id>` 의사 노드 + 표현식 컨텍스트."""

    def __init__(self, inputs: Optional[Dict[str, Any]] = None, node_outputs: Optional[Dict[str, Dict[str, Any]]] = None):
        self.logs: List[Dict[str, Any]] = []
        self._inputs = inputs or {}
        self._node_outputs = node_outputs or {}
        self.is_dry_run = True
        self.is_deep_validate = False
        self._iteration_item: Any = None
        self._iteration_index = 0
        self._iteration_total = 0

    def log(self, level: str, message: str, node_id: Optional[str] = None, data: Any = None) -> None:
        self.logs.append({"level": level, "message": message, "node_id": node_id})

    def get_output(self, node_id: str, port_name: Optional[str] = None) -> Any:
        if node_id.startswith("_input_"):
            return self._inputs if port_name is None else self._inputs.get(port_name)
        outs = self._node_outputs.get(node_id, {})
        return outs if port_name is None else outs.get(port_name)

    def get_all_outputs(self, node_id: str) -> Dict[str, Any]:
        if node_id.startswith("_input_"):
            return dict(self._inputs)
        return dict(self._node_outputs.get(node_id, {}))

    def get_expression_context(self):
        from programgarden_core.expression.evaluator import ExpressionContext
        return ExpressionContext(
            node_outputs={k: dict(v) for k, v in self._node_outputs.items()},
            item=self._iteration_item,
            index=self._iteration_index,
            total=self._iteration_total,
        )

    def record_deep_unresolved_binding(self, *a, **k) -> None:  # evaluate_all_bindings 가 호출
        pass

    def warnings_with(self, needle: str) -> List[str]:
        return [l["message"] for l in self.logs if l["level"] == "warning" and needle.lower() in l["message"].lower()]

    def infos_with(self, needle: str) -> List[str]:
        return [l["message"] for l in self.logs if l["level"] == "info" and needle.lower() in l["message"].lower()]


def _wf(node_id: str, raw_config: Dict[str, Any]):
    return SimpleNamespace(nodes={node_id: SimpleNamespace(config=raw_config)})


# ---------------------------------------------------------------------------
# 1. 분류기 단위
# ---------------------------------------------------------------------------

def test_bound_expression_that_evaluated_empty_is_no_signal():
    raw = {"symbols": "{{ nodes.rsi.passed_symbols }}", "method": "fixed_quantity"}
    evaluated = {"symbols": [], "method": "fixed_quantity"}
    kind, detail = classify_empty_symbol_source("sizing", evaluated, _Ctx(), _wf("sizing", raw))
    assert kind == EMPTY_SYMBOLS_NO_SIGNAL
    assert "nodes.rsi.passed_symbols" in detail


def test_edge_input_port_empty_list_is_no_signal():
    """설정엔 symbols 가 없지만 엣지로 상류 symbols=[] 가 들어온 경우."""
    kind, _ = classify_empty_symbol_source(
        "sizing", {"method": "fixed_quantity"}, _Ctx(inputs={"symbols": []}), _wf("sizing", {"method": "fixed_quantity"})
    )
    assert kind == EMPTY_SYMBOLS_NO_SIGNAL


def test_no_source_at_all_is_unbound():
    kind, detail = classify_empty_symbol_source(
        "sizing", {"method": "fixed_quantity"}, _Ctx(), _wf("sizing", {"method": "fixed_quantity"})
    )
    assert kind == EMPTY_SYMBOLS_UNBOUND
    assert "passed_symbols" in detail  # actionable hint names the canonical sources


def test_unresolved_node_reference_is_unresolved():
    """벤치 실측: `symbol: {{ nodes.split.item }}` 인데 split 노드가 DSL 에 없다."""
    evaluated = {"symbol": "{{ nodes.split.item }}"}
    kind, detail = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(), _wf("historical", dict(evaluated)), keys=("symbol", "symbols")
    )
    assert kind == EMPTY_SYMBOLS_UNRESOLVED
    assert "nodes.split.item" in detail and "did not resolve" in detail


def test_item_binding_outside_loop_with_empty_upstream_array_is_no_signal():
    """`symbol: {{ item }}` 인데 상류 배열(symbols)이 비어 반복이 안 일어난 경우 — 정상."""
    evaluated = {"symbol": "{{ item }}"}
    kind, detail = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(inputs={"symbols": [], "count": 0}), _wf("historical", dict(evaluated)),
        keys=("symbol", "symbols"),
    )
    assert kind == EMPTY_SYMBOLS_NO_SIGNAL
    assert "empty" in detail


def test_item_binding_outside_loop_without_array_source_is_unresolved():
    """`symbol: {{ item }}` 인데 상류에 배열 포트가 아예 없다 — 설계 결함."""
    evaluated = {"symbol": "{{ item }}"}
    kind, detail = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(inputs={"balance": {"cash": 1}}), _wf("historical", dict(evaluated)),
        keys=("symbol", "symbols"),
    )
    assert kind == EMPTY_SYMBOLS_UNRESOLVED
    assert "not being iterated" in detail


def test_item_binding_with_non_empty_upstream_array_is_unresolved():
    """배열은 있는데(비어 있지 않음) 반복이 안 걸렸다 — 이 노드까지 배열이 안 흘렀다는 뜻."""
    evaluated = {"symbol": "{{ item }}"}
    kind, _ = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(inputs={"values": [{"x": 1}]}), _wf("historical", dict(evaluated)),
        keys=("symbol", "symbols"),
    )
    assert kind == EMPTY_SYMBOLS_UNRESOLVED


def test_literal_list_with_unusable_entries_is_unbound():
    raw = {"symbols": [1, 2]}
    kind, detail = classify_empty_symbol_source("sizing", {"symbols": []}, _Ctx(), _wf("sizing", raw))
    assert kind == EMPTY_SYMBOLS_UNBOUND and "literal list" in detail


def test_without_workflow_falls_back_to_evaluated_config():
    """workflow 가 없으면(레거시/테스트 호출) 평가된 설정만 본다 — 미해석 표현식은 여전히 잡는다."""
    kind, _ = classify_empty_symbol_source("n", {"symbols": "{{ nodes.x.y }}"}, _Ctx(), None)
    assert kind == EMPTY_SYMBOLS_UNRESOLVED
    kind, _ = classify_empty_symbol_source("n", {}, _Ctx(), None)
    assert kind == EMPTY_SYMBOLS_UNBOUND


# ---------------------------------------------------------------------------
# 2. PositionSizingNodeExecutor — 벤치 실측 모양 그대로
# ---------------------------------------------------------------------------

def _run_sizing(raw: Dict[str, Any], ctx: _Ctx, evaluated: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ex = PositionSizingNodeExecutor()
    return asyncio.run(ex.execute(
        node_id="sizing", node_type="PositionSizingNode",
        config=dict(evaluated if evaluated is not None else raw), context=ctx,
        workflow=_wf("sizing", raw),
    ))


def test_sizing_bound_condition_with_no_pass_today_is_no_signal_without_warning():
    """본선 최다 실패 모양: `symbols: {{ nodes.rsi.passed_symbols }}`, fixed_quantity 1, 오늘 통과 0."""
    raw = {"symbols": "{{ nodes.rsi.passed_symbols }}", "method": "fixed_quantity", "fixed_quantity": 1,
           "balance": "{{ nodes.account.balance }}"}
    ctx = _Ctx(node_outputs={"rsi": {"passed_symbols": [], "is_condition_met": False},
                             "account": {"balance": {"orderable_amount": 1000}}})
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.NO_SIGNAL.value
    assert out["orders"] == []
    assert not ctx.warnings_with("No symbols provided"), ctx.logs
    assert ctx.infos_with("No symbols to size")


def test_sizing_unbound_symbols_keeps_warning_and_no_symbol():
    raw = {"method": "fixed_quantity", "fixed_quantity": 1}
    ctx = _Ctx()
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.NO_SYMBOL.value
    warns = ctx.warnings_with("No symbols provided for position sizing")
    assert warns and "no symbol source" in warns[0]
    assert out["detail"] and "passed_symbols" in out["detail"]


def test_sizing_unresolved_binding_keeps_warning_with_expression():
    raw = {"symbols": "{{ nodes.trigger_combine.result }}", "method": "fixed_quantity"}
    ctx = _Ctx()  # trigger_combine 출력 없음 → 표현식 미해석 → 리터럴 유지
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.NO_SYMBOL.value
    warns = ctx.warnings_with("No symbols provided for position sizing")
    assert warns and "nodes.trigger_combine.result" in warns[0]


def test_sizing_upstream_error_dict_is_fetch_failed_with_warning():
    raw = {"symbols": "{{ nodes.market.result }}", "method": "fixed_percent"}
    ctx = _Ctx(node_outputs={"market": {"result": {"error": "LS timeout", "values": []}}})
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.FETCH_FAILED.value
    assert ctx.warnings_with("upstream fetch failed")


# ---------------------------------------------------------------------------
# 3. HistoricalDataNodeExecutor / MarketDataNodeExecutor
# ---------------------------------------------------------------------------

def _run_hist(raw: Dict[str, Any], ctx: _Ctx) -> Dict[str, Any]:
    ex = HistoricalDataNodeExecutor()
    return asyncio.run(ex.execute(
        node_id="historical", node_type="OverseasStockHistoricalDataNode",
        config=dict(raw), context=ctx, workflow=_wf("historical", raw),
    ))


def test_historical_item_binding_with_empty_upstream_is_info_not_warning():
    raw = {"symbol": "{{ item }}", "interval": "1d"}
    ctx = _Ctx(inputs={"symbols": []})
    out = _run_hist(raw, ctx)
    assert out == {"value": None, "values": [], "symbols": [], "period": "", "interval": "1d"}
    assert not ctx.warnings_with("No symbols provided")
    assert ctx.infos_with("No symbols to fetch")


def test_historical_unresolved_split_reference_keeps_warning():
    raw = {"symbol": "{{ nodes.split.item }}", "interval": "1d"}
    ctx = _Ctx()
    out = _run_hist(raw, ctx)
    assert out["values"] == []
    warns = ctx.warnings_with("No symbols provided")
    assert warns and "nodes.split.item" in warns[0]


def test_historical_no_source_keeps_warning():
    ctx = _Ctx()
    _run_hist({"interval": "1d"}, ctx)
    assert ctx.warnings_with("No symbols provided")


def _run_market(raw: Dict[str, Any], ctx: _Ctx, evaluated: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ex = MarketDataNodeExecutor()
    return asyncio.run(ex.execute(
        node_id="market", node_type="OverseasStockMarketDataNode",
        config=dict(evaluated if evaluated is not None else raw), context=ctx, workflow=_wf("market", raw),
    ))


def test_market_bound_filter_empty_is_values_without_error():
    raw = {"symbols": "{{ nodes.filter.symbols }}"}
    ctx = _Ctx(node_outputs={"filter": {"symbols": []}})
    out = _run_market(raw, ctx)
    assert out == {"values": []}
    assert not [l for l in ctx.logs if l["level"] == "error"]
    assert ctx.infos_with("No symbols to quote")


def test_market_no_source_keeps_error():
    ctx = _Ctx()
    out = _run_market({}, ctx)
    assert "error" in out and "symbols 필드가 필수" in out["error"]
    assert [l for l in ctx.logs if l["level"] == "error"]


# ---------------------------------------------------------------------------
# 4. NewOrderNodeExecutor — 상류 no_signal 물려받기 (runtime 관측성)
# ---------------------------------------------------------------------------

def test_order_inherits_upstream_no_signal_from_input_namespace():
    ctx = _Ctx(inputs={"orders": [], "order": None, "symbols": [], "reason": "no_signal",
                       "message": "No trading signal today (upstream produced an empty result normally).",
                       "detail": "upstream symbol source produced no symbols in this run (no signal)"})
    reason, detail = NewOrderNodeExecutor()._diagnose_empty_reason(None, {}, None, ctx, node_id="order")
    assert reason == EmptyOrderReason.NO_SIGNAL
    assert "no signal" in detail


def test_order_inherits_upstream_no_signal_via_raw_order_expr():
    ctx = _Ctx(node_outputs={"sizing": {"orders": [], "order": None, "reason": "no_signal", "detail": "d"}})
    reason, _ = NewOrderNodeExecutor()._diagnose_empty_reason(None, {}, "{{ nodes.sizing.order }}", ctx, node_id="order")
    assert reason == EmptyOrderReason.NO_SIGNAL


def test_order_still_no_symbol_when_upstream_says_no_symbol():
    ctx = _Ctx(inputs={"orders": [], "reason": "no_symbol", "detail": "no symbol source is configured"})
    reason, _ = NewOrderNodeExecutor()._diagnose_empty_reason(None, {}, None, ctx, node_id="order")
    assert reason == EmptyOrderReason.NO_SYMBOL


def test_order_upstream_no_signal_with_error_marker_stays_fetch_failed():
    """no_signal 이라도 실패 마커(_partial_failure)가 같이 있으면 정상으로 물려받지 않는다."""
    ctx = _Ctx(inputs={"orders": [], "reason": "no_signal", "_partial_failure": True,
                       "_failure_reason": "balance fetch partially failed"})
    reason, _ = NewOrderNodeExecutor()._diagnose_empty_reason(None, {}, None, ctx, node_id="order")
    assert reason != EmptyOrderReason.NO_SIGNAL


# ---------------------------------------------------------------------------
# 5. 적대 리뷰(2026-09-07) 반영 — 분류기가 결함을 no_signal 로 삼키지 않는다
# ---------------------------------------------------------------------------

from programgarden.executor import EMPTY_SYMBOLS_UPSTREAM_FAILED  # noqa: E402


def test_non_empty_input_port_without_binding_is_unbound():
    """엣지로 symbols 가 들어왔는데(비어 있지 않음) 이 노드가 빈 목록을 봤다 = 바인딩 누락."""
    kind, detail = classify_empty_symbol_source(
        "sizing", {"method": "fixed_quantity"},
        _Ctx(inputs={"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}),
        _wf("sizing", {"method": "fixed_quantity"}),
    )
    assert kind == EMPTY_SYMBOLS_UNBOUND
    assert "no `symbols` binding" in detail


def test_item_binding_with_condition_zero_pass_is_no_signal_despite_other_lists():
    """ConditionNode 0건 통과: passed_symbols=[] 이지만 symbols/failed_symbols 는 비어 있지 않다."""
    evaluated = {"symbol": "{{ item }}"}
    inputs = {
        "passed_symbols": [],
        "failed_symbols": [{"symbol": "AAPL"}, {"symbol": "MSFT"}],
        "symbols": [{"symbol": "AAPL"}, {"symbol": "MSFT"}],
        "symbol_results": [{"symbol": "AAPL", "passed": False}],
        "is_condition_met": False,
    }
    kind, _ = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(inputs=inputs), _wf("historical", dict(evaluated)),
        keys=("symbol", "symbols"),
    )
    assert kind == EMPTY_SYMBOLS_NO_SIGNAL


def test_item_binding_with_condition_pass_but_no_iteration_is_unresolved():
    evaluated = {"symbol": "{{ item }}"}
    inputs = {"passed_symbols": [{"symbol": "AAPL"}], "symbols": [{"symbol": "AAPL"}]}
    kind, _ = classify_empty_symbol_source(
        "historical", evaluated, _Ctx(inputs=inputs), _wf("historical", dict(evaluated)),
        keys=("symbol", "symbols"),
    )
    assert kind == EMPTY_SYMBOLS_UNRESOLVED


@pytest.mark.parametrize("scalar", [False, True, 0, 3, "AAPL"])
def test_binding_resolved_to_scalar_is_unresolved(scalar):
    raw = {"symbols": "{{ nodes.cond.is_condition_met }}", "method": "fixed_quantity"}
    kind, detail = classify_empty_symbol_source("sizing", {"symbols": scalar}, _Ctx(), _wf("sizing", raw))
    assert kind == EMPTY_SYMBOLS_UNRESOLVED
    assert "not a symbol list" in detail


def test_referenced_node_error_is_upstream_failed():
    raw = {"symbols": "{{ nodes.market.values }}", "method": "fixed_percent"}
    ctx = _Ctx(node_outputs={"market": {"values": [], "error": "MARKET_DATA_FETCH_FAILED: LS timeout"}})
    kind, detail = classify_empty_symbol_source("sizing", {"symbols": []}, ctx, _wf("sizing", raw))
    assert kind == EMPTY_SYMBOLS_UPSTREAM_FAILED
    assert "LS timeout" in detail


def test_sizing_referenced_node_error_returns_fetch_failed_with_warning():
    raw = {"symbols": "{{ nodes.market.values }}", "method": "fixed_percent", "balance": {"orderable_amount": 100}}
    ctx = _Ctx(node_outputs={"market": {"values": [], "error": "MARKET_DATA_FETCH_FAILED: LS timeout"}})
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.FETCH_FAILED.value
    assert ctx.warnings_with("No symbols provided for position sizing")
    assert "LS timeout" in out["detail"]


def test_sizing_missing_balance_is_fetch_failed_not_no_signal():
    """종목은 있는데 balance 바인딩이 없다 — 주문 노드가 D2 상속으로 조용히 no-op 되면 안 된다."""
    raw = {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "method": "fixed_percent", "max_percent": 5}
    ctx = _Ctx()
    out = _run_sizing(raw, ctx)
    assert out["reason"] == EmptyOrderReason.FETCH_FAILED.value
    assert "balance" in out["detail"]


def test_sizing_zero_cash_with_balance_present_is_no_signal():
    raw = {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "method": "fixed_percent",
           "balance": {"orderable_amount": 0}}
    out = _run_sizing(raw, _Ctx())
    assert out["reason"] == EmptyOrderReason.NO_SIGNAL.value


def test_sizing_unresolved_balance_literal_is_fetch_failed():
    raw = {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "method": "fixed_percent",
           "balance": "{{ nodes.ghost.balance }}"}
    out = _run_sizing(raw, _Ctx(), evaluated={**raw, "balance": None})
    assert out["reason"] == EmptyOrderReason.FETCH_FAILED.value

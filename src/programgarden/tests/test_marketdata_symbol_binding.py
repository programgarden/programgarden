"""MarketDataNode (및 형제) symbol 바인딩 회귀 테스트.

배경 (호스트 실키 라이브에서 확정된 버그):
메인 루프의 `_resolve_config_expressions` 는 `ExpressionEvaluator.evaluate_fields`
를 쓰는데, 이 함수는 list 항목이 dict 이면 재귀하지 않아
`symbols: [{"symbol": "{{ ... }}"}]` 의 중첩 표현식을 literal 문자열로 남긴다.
전용 executor(MarketDataNode/Fundamental/Watchlist)는 `evaluate_all_bindings`
(dict/list 완전 재귀)를 직접 호출해야 LS API 에 해석된 종목코드를 전달한다.

이 테스트는 (1) evaluate_fields 가 중첩을 못 푼다는 사실(버그 재현)과
(2) evaluate_all_bindings 가 푼다는 사실(수정 검증)을 함께 고정한다.
"""

from programgarden_core.expression.evaluator import (
    ExpressionContext,
    ExpressionEvaluator,
)
from programgarden.executor import evaluate_all_bindings


NODE_OUTPUTS = {
    "top2": {
        "symbols": [
            {"symbol": "MMM", "exchange": "NASDAQ"},
            {"symbol": "AAPL", "exchange": "NASDAQ"},
        ]
    }
}

NESTED_CONFIG = {
    "symbols": [
        {
            "symbol": "{{ nodes.top2.symbols[0].symbol }}",
            "exchange": "{{ nodes.top2.symbols[0].exchange }}",
        }
    ],
    "fields": ["price"],
    "connection": {"product": "overseas_stock", "appkey": "secret"},
}


class _FakeExecCtx:
    """evaluate_all_bindings 가 요구하는 최소 ExecutionContext 대역."""

    def __init__(self, node_outputs):
        self._ec = ExpressionContext(node_outputs=node_outputs)

    def get_expression_context(self):
        return self._ec

    def log(self, *args, **kwargs):
        pass


def test_evaluate_fields_does_not_recurse_into_list_of_dict():
    """버그 재현: 메인 루프 경로는 list-of-dict 중첩 표현식을 literal 로 남긴다."""
    ev = ExpressionEvaluator(ExpressionContext(node_outputs=NODE_OUTPUTS))
    out = ev.evaluate_fields({k: v for k, v in NESTED_CONFIG.items()})
    # 중첩 표현식이 해석되지 않고 literal 로 남아 있어야 한다 (이 한계 때문에
    # 전용 executor 가 evaluate_all_bindings 를 호출해야 함).
    assert out["symbols"][0]["symbol"] == "{{ nodes.top2.symbols[0].symbol }}"
    assert out["symbols"][0]["exchange"] == "{{ nodes.top2.symbols[0].exchange }}"


def test_evaluate_all_bindings_resolves_nested_symbols():
    """수정 검증: evaluate_all_bindings 는 list-of-dict 중첩을 완전 해석한다."""
    out = evaluate_all_bindings(
        {k: v for k, v in NESTED_CONFIG.items()},
        _FakeExecCtx(NODE_OUTPUTS),
        "market_a",
    )
    assert out["symbols"] == [{"symbol": "MMM", "exchange": "NASDAQ"}]


def test_evaluate_all_bindings_preserves_resolved_and_injected_values():
    """이미 해석된 값/주입된 connection dict 는 그대로 보존(이중 평가 무해)."""
    out = evaluate_all_bindings(
        {k: v for k, v in NESTED_CONFIG.items()},
        _FakeExecCtx(NODE_OUTPUTS),
        "market_a",
    )
    assert out["fields"] == ["price"]
    assert out["connection"] == {"product": "overseas_stock", "appkey": "secret"}


def test_evaluate_all_bindings_second_pass_is_idempotent():
    """메인 루프가 일부 해석한 뒤 executor 가 다시 호출해도 안전(멱등)."""
    once = evaluate_all_bindings(
        {k: v for k, v in NESTED_CONFIG.items()},
        _FakeExecCtx(NODE_OUTPUTS),
        "market_a",
    )
    twice = evaluate_all_bindings(once, _FakeExecCtx(NODE_OUTPUTS), "market_a")
    assert twice["symbols"] == [{"symbol": "MMM", "exchange": "NASDAQ"}]
    assert twice == once

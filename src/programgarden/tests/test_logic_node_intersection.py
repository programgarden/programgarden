"""Unit tests for LogicNode `all` (AND) intersection semantics.

These tests exercise LogicNodeExecutor directly (via _apply_operator and
execute) with a lightweight stub context, so they need no credentials and
run fully offline. They lock in the two core bugfixes:

  Bug A: is_condition_met arriving as a merged list under multi-symbol
         auto-iterate must be scalarised with any(), not bool(list).
  Bug B: an empty (but explicitly provided) passed_symbols list must zero
         out the AND intersection instead of being silently dropped.
"""
import asyncio

import pytest

from programgarden.executor import LogicNodeExecutor
from programgarden_core.expression.evaluator import ExpressionContext


class _StubContext:
    """Minimal context: LogicNodeExecutor only calls context.log()."""

    def __init__(self):
        self.warnings = []

    def log(self, level, message, node_id=None, *args, **kwargs):
        if level == "warning":
            self.warnings.append(message)

    def get_expression_context(self):
        # No {{ }} expressions used in these tests; an empty context suffices.
        return ExpressionContext()


def _codes(passed):
    return sorted(
        s.get("symbol") if isinstance(s, dict) else s for s in passed
    )


def _apply_all(results):
    """Run _apply_operator('all', ...) from a list of condition_result dicts."""
    ctx = _StubContext()
    exe = LogicNodeExecutor()
    all_passed = [r["passed_symbols"] for r in results]
    weights = {r["index"]: r.get("weight", 1.0) for r in results}
    final_result, final_passed = exe._apply_operator(
        operator="all",
        results=results,
        all_passed_symbols=all_passed,
        threshold=None,
        weights=weights,
        context=ctx,
        node_id="logic",
    )
    return final_result, _codes(final_passed)


def _cond(index, result, passed_symbols, symbols_provided=True, weight=1.0):
    return {
        "index": index,
        "result": result,
        "passed_symbols": passed_symbols,
        "symbols_provided": symbols_provided,
        "weight": weight,
    }


# --- Bug B: intersection accuracy --------------------------------------


def test_all_overlapping_intersection():
    """Both sides symbol-bearing and overlapping -> intersection."""
    results = [
        _cond(0, True, [{"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NYSE", "symbol": "JPM"}]),
        _cond(1, True, [{"exchange": "NYSE", "symbol": "JPM"},
                        {"exchange": "NASDAQ", "symbol": "MSFT"}]),
    ]
    final_result, passed = _apply_all(results)
    assert final_result is True
    assert passed == ["JPM"]


def test_all_empty_operand_zeroes_intersection():
    """One side explicitly empty (symbol-bearing) -> intersection is []."""
    results = [
        _cond(0, False, []),  # rsi passed nothing, but explicitly provided
        _cond(1, True, [{"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NYSE", "symbol": "JPM"}]),
    ]
    final_result, passed = _apply_all(results)
    # AND with a falsy condition -> overall False, passed empty.
    assert final_result is False
    assert passed == []


def test_all_empty_operand_zeroes_even_when_both_true():
    """Empty symbol-bearing list zeroes intersection even if bools are True."""
    results = [
        _cond(0, True, []),  # provided-but-empty, yet flagged True
        _cond(1, True, [{"exchange": "NASDAQ", "symbol": "AAPL"}]),
    ]
    final_result, passed = _apply_all(results)
    assert final_result is True  # both bools True
    assert passed == []  # but intersection with [] is empty


def test_all_no_overlap_intersection_empty():
    results = [
        _cond(0, True, [{"exchange": "NASDAQ", "symbol": "AAPL"}]),
        _cond(1, True, [{"exchange": "NYSE", "symbol": "JPM"}]),
    ]
    final_result, passed = _apply_all(results)
    assert final_result is True
    assert passed == []


# --- boolean-gate compatibility ----------------------------------------


def test_all_boolean_gate_does_not_zero_intersection():
    """A boolean-gate condition (symbols not provided) must not collapse the
    intersection to []; only symbol-bearing conditions participate."""
    results = [
        _cond(0, True, [{"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NYSE", "symbol": "JPM"}]),
        _cond(1, True, [], symbols_provided=False),  # pure boolean gate
    ]
    final_result, passed = _apply_all(results)
    assert final_result is True
    assert passed == ["AAPL", "JPM"]


def test_all_boolean_gate_false_blocks():
    """A boolean gate evaluating False blocks the AND result."""
    results = [
        _cond(0, True, [{"exchange": "NASDAQ", "symbol": "AAPL"}]),
        _cond(1, False, [], symbols_provided=False),
    ]
    final_result, passed = _apply_all(results)
    assert final_result is False
    assert passed == []


# --- Bug A: is_condition_met list scalarisation (via execute) -----------


def _run_execute(conditions, operator="all"):
    exe = LogicNodeExecutor()
    ctx = _StubContext()

    async def _go():
        return await exe.execute(
            node_id="logic",
            node_type="LogicNode",
            config={"operator": operator, "conditions": conditions},
            context=ctx,
        )

    return asyncio.run(_go()), ctx


def test_execute_list_is_condition_met_scalarised_false():
    """is_condition_met=[False, False, ...] must scalarise to False, not be
    treated as truthy (non-empty list)."""
    conditions = [
        {
            "is_condition_met": [False, False, False, False, False],
            "passed_symbols": [],
        },
        {
            "is_condition_met": [True, False, False, False, True],
            "passed_symbols": [
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NYSE", "symbol": "JPM"},
            ],
        },
    ]
    out, ctx = _run_execute(conditions)
    # condition 0 scalarises to False -> overall AND False -> passed []
    assert out["result"] is False
    assert _codes(out["passed_symbols"]) == []
    assert out["details"][0]["result"] is False
    assert out["details"][1]["result"] is True
    # no missing-is_condition_met warnings since both provided
    assert not any("missing 'is_condition_met'" in w for w in ctx.warnings)


def test_execute_list_is_condition_met_scalarised_true():
    conditions = [
        {
            "is_condition_met": [True, False, True],
            "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
        },
        {
            "is_condition_met": [False, True, False],
            "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
        },
    ]
    out, _ = _run_execute(conditions)
    assert out["result"] is True
    assert _codes(out["passed_symbols"]) == ["AAPL"]


def test_execute_scalar_is_condition_met_still_works():
    conditions = [
        {"is_condition_met": True,
         "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
        {"is_condition_met": True,
         "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
    ]
    out, _ = _run_execute(conditions)
    assert out["result"] is True
    assert _codes(out["passed_symbols"]) == ["AAPL"]


def test_execute_missing_is_condition_met_warns_and_false():
    conditions = [
        {"passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
        {"is_condition_met": True,
         "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
    ]
    out, ctx = _run_execute(conditions)
    assert out["result"] is False
    assert any("missing 'is_condition_met'" in w for w in ctx.warnings)


def test_execute_mixed_boolean_gate_with_symbol_bearing():
    """End-to-end: one symbol-bearing list + one boolean gate (no symbols)."""
    conditions = [
        {
            "is_condition_met": [True, False, True],
            "passed_symbols": [
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NYSE", "symbol": "JPM"},
            ],
        },
        {
            # boolean gate: no passed_symbols key at all
            "is_condition_met": True,
        },
    ]
    out, _ = _run_execute(conditions)
    assert out["result"] is True
    # symbol-bearing intersection only; gate must not zero it
    assert _codes(out["passed_symbols"]) == ["AAPL", "JPM"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

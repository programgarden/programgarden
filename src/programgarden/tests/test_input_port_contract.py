"""Input-side declaration==runtime contract tests.

The 1.28.0 contract tests asserted OUTPUT ports are actually returned. This is
the mirror image: DECLARED INPUT ports/fields must actually be READ by the
executor. The `symbol` bug (2026-07-14) was exactly this class — the realtime
market nodes declared a `symbol` InputPort (+ field + FieldSchema + every _usage
example) that `_resolve_symbols` never read, so per-symbol bindings silently
fell through to the ancestor account's full held_symbols list (Split fan-out
became decorative).

Two layers:
  1. Behavioral — `_resolve_symbols` honors the declared `symbol` field.
  2. Family-wide static — every declared (non-control-flow) input port name is
     referenced by its executor, except a documented allowlist. Catches the
     next input-port drift the moment someone adds a dead declared port.
"""
import inspect
import re

import pytest

from programgarden.executor import RealMarketDataNodeExecutor, WorkflowExecutor
from programgarden_core.exceptions import ValidationError
from programgarden_core.registry.node_registry import NodeTypeRegistry


# --------------------------------------------------------------------------- #
# Minimal ExecutionContext stub for _resolve_symbols
# --------------------------------------------------------------------------- #
class _FakeCtx:
    def __init__(self, inputs=None, parents=None):
        # inputs: {(node_id, port): value}  parents: {(node_id, type): output}
        self._inputs = inputs or {}
        self._parents = parents or {}

    def get_output(self, node_id, port_name=None):
        return self._inputs.get((node_id, port_name))

    def find_parent_output(self, node_id, target_type):
        return self._parents.get((node_id, target_type))

    def log(self, *a, **k):
        pass


NASDAQ_AAPL = {"exchange": "NASDAQ", "exchange_code": "82", "symbol": "AAPL"}


# --------------------------------------------------------------------------- #
# 1. Behavioral — the fix
# --------------------------------------------------------------------------- #
def _resolve(config, ctx=None):
    ex = RealMarketDataNodeExecutor()
    return ex._resolve_symbols("real", config, ctx or _FakeCtx(), None)


def test_declared_symbol_dict_is_honored():
    """The declared `symbol` field is READ and returned as the sole subscription."""
    assert _resolve({"symbol": NASDAQ_AAPL}) == [NASDAQ_AAPL]


def test_symbol_wins_over_account_fallback():
    """When `symbol` is set, it is used — NOT the ancestor account's full list."""
    ctx = _FakeCtx(parents={("real", "OverseasStockRealAccountNode"): {
        "held_symbols": [NASDAQ_AAPL, {"exchange": "NASDAQ", "exchange_code": "82", "symbol": "TSLA"}]
    }})
    # bound to one branch symbol → only that symbol, not both held symbols
    assert _resolve({"symbol": {"exchange": "NASDAQ", "symbol": "TSLA"}}, ctx) == [
        {"exchange": "NASDAQ", "symbol": "TSLA"}
    ]


def test_symbol_string_raises_not_silent():
    """A non-dict `symbol` (e.g. bound to `.item.symbol`) raises, never silently skipped."""
    with pytest.raises(ValidationError):
        _resolve({"symbol": "AAPL"})


def test_symbol_dict_without_symbol_key_raises():
    with pytest.raises(ValidationError):
        _resolve({"symbol": {"exchange": "NASDAQ"}})


def test_no_symbol_falls_back_to_account_held_symbols():
    """Auto-iterate pattern (account → real_market, no Split) still works via fallback."""
    ctx = _FakeCtx(parents={("real", "OverseasStockRealAccountNode"): {
        "held_symbols": [NASDAQ_AAPL]
    }})
    assert _resolve({}, ctx) == [NASDAQ_AAPL]


def test_undeclared_symbols_plural_config_is_no_longer_consumed():
    """`symbols` (plural) was consumed-but-not-declared drift — now removed.

    With only `symbols` config set (no declared `symbol`, no account), resolution
    must NOT pick it up; it falls through to empty.
    """
    assert _resolve({"symbols": [NASDAQ_AAPL]}) == []


# --------------------------------------------------------------------------- #
# 2. Family-wide static input-port consumption contract
# --------------------------------------------------------------------------- #
# Control-flow / framework-delivered ports: arrive via edges, not read by name.
_FRAMEWORK_PORTS = {"trigger", "item", "data", "input", "connection"}

# Declared input ports that are legitimately not read as a literal in their
# executor source, with the reason. Adding to this list is a deliberate act.
_KNOWN_UNCONSUMED = {
    # consumed via workflow-graph traversal (get_tool_node_ids / LLMModelNode
    # wiring), not by a config literal in AIAgentNodeExecutor:
    ("AIAgentNode", "ai_model"),
    ("AIAgentNode", "tools"),
    # allocated_capital is read by PortfolioNodeExecutor (_input_ port), not by
    # BacktestEngineNodeExecutor's own source:
    ("BacktestEngineNode", "allocated_capital"),
    # account_state: declared optional ("실거래용, 선택적") forward port, not yet
    # consumed. Tracked as a follow-up (lower severity: optional, not corpus-wide).
    ("PortfolioNode", "account_state"),
}


def _declared_data_inputs(node_cls):
    inp = getattr(node_cls, "_inputs", None)
    if inp is not None and inp.__class__.__name__ == "ModelPrivateAttr":
        inp = getattr(inp, "default", None)
    names = set()
    for p in inp or []:
        n = getattr(p, "name", None)
        t = getattr(p, "type", None)
        if n and n not in _FRAMEWORK_PORTS and t != "trigger":
            names.add(n)
    return names


def _dead_ports():
    wx = WorkflowExecutor()
    reg = NodeTypeRegistry()
    src_cache = {}
    dead = set()
    for nt, ex in wx._executors.items():
        if type(ex).__name__ == "GenericNodeExecutor":
            continue
        try:
            cls = reg.get(nt)
        except Exception:
            cls = None
        if cls is None:
            continue
        inputs = _declared_data_inputs(cls)
        if not inputs:
            continue
        c = type(ex)
        if c not in src_cache:
            try:
                src_cache[c] = inspect.getsource(c)
            except Exception:
                src_cache[c] = ""
        src = src_cache[c]
        for name in inputs:
            if not re.search(rf'["\']{re.escape(name)}["\']', src):
                dead.add((nt, name))
    return dead


def test_realtime_market_symbol_input_is_consumed():
    """Regression lock: the 3 realtime market nodes' declared `symbol` is read."""
    dead = _dead_ports()
    for nt in (
        "OverseasStockRealMarketDataNode",
        "KoreaStockRealMarketDataNode",
        "OverseasFuturesRealMarketDataNode",
    ):
        assert (nt, "symbol") not in dead, f"{nt}.symbol declared but not consumed (regression)"


def test_no_new_dead_input_ports():
    """No declared data input port is unconsumed beyond the documented allowlist.

    A NEW entry here means someone declared an input port the executor never
    reads — the `symbol` bug class. Vet it, fix it, or justify it in
    _KNOWN_UNCONSUMED with a reason.
    """
    dead = _dead_ports()
    unexpected = dead - _KNOWN_UNCONSUMED
    assert not unexpected, (
        f"Undeclared-consumption drift — declared input ports not read by executor: "
        f"{sorted(unexpected)}"
    )

"""A realtime re-trigger keeps the startup snapshot outputs visible to the guard.

Regression for the recurring-trigger safety property behind the paid realtime
trading probe: a guard that JOINS a live tick stream with startup snapshot nodes
(account / open_orders queried once upstream of the stream) must keep seeing
those snapshots on EVERY subsequent tick. The re-trigger path re-executes only
the tick's downstream chain (guard -> gate -> ...); the account/open_orders nodes
are UPSTREAM of the guard, never in that set, so their outputs are neither
re-recorded nor cleared and the guard resolves ``{{ nodes.open_orders.* }}`` /
``{{ nodes.account.* }}`` from the retained context outputs. A guard that forbids
a buy while an open order exists (or while holding) therefore STAYS blocked after
the tick — for replay and, on the same executor path, for live.

This locks in ``WorkflowJob._handle_realtime_update``: ``_find_trigger_nodes``
returns only the tick's direct successors, ``_find_downstream_nodes`` walks
forward from there, and the ``_outputs.pop`` calls touch only that re-executed
chain (and gated/failed nodes) — never an upstream snapshot node.
"""
import pytest

from programgarden.replay_external import recording
from programgarden.replay_scenarios import check_final_expectations
from programgarden.validation_replay import replay

AS_OF = "2026-09-22T14:00:00Z"
LATER = "2026-09-22T14:00:30Z"
CONN = {"provider": "ls-sec.co.kr", "product": "overseas_stock"}

# Blocks on ANY listed open order (len > 0) or ANY held position — never derives a
# `remaining_quantity` from a row that may omit it (an OpenOrdersNode lists only
# still-open orders, so its presence is the block).
GUARD = (
    "def execute(data, params, context):\n"
    " bars = (params.get('tick') or {}).get('A') or []\n"
    " price = bars[-1].get('close') if bars else None\n"
    " open_orders = params.get('open_orders') or []\n"
    " positions = params.get('positions') or []\n"
    " allowed = price is not None and price <= 150 and len(open_orders) == 0 and len(positions) == 0\n"
    " return {'allowed': allowed}\n")


def _feed_rec(at, price):
    bars = {"A": [{"symbol": "A", "exchange": "NASDAQ", "date": "20260922",
                   "open": price, "high": price, "low": price, "close": price, "volume": 10}]}
    return recording("OverseasStockRealMarketDataNode",
                     {"symbol": {"symbol": "A", "exchange": "NASDAQ"}, "connection": CONN},
                     {"data": bars, "ohlcv_data": bars, "symbols": [{"symbol": "A", "exchange": "NASDAQ"}]},
                     {"type": "object", "required": ["data", "ohlcv_data", "symbols"]}, as_of=at)


def build(open_rows, positions):
    # The guard ALLOWS only when the snapshot is clear (no open order and no holding).
    allow = len(open_rows) == 0 and len(positions) == 0
    nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        {"id": "account", "type": "OverseasStockAccountNode"},
        {"id": "open_orders", "type": "OverseasStockOpenOrdersNode"},
        {"id": "feed", "type": "OverseasStockRealMarketDataNode", "symbol": {"symbol": "A", "exchange": "NASDAQ"}},
        {"id": "guard", "type": "CodeNode",
         "params": {"tick": "{{ nodes.feed.data }}", "open_orders": "{{ nodes.open_orders.open_orders }}",
                    "positions": "{{ nodes.account.positions }}"},
         "outputs": [{"name": "allowed", "type": "boolean"}], "code": GUARD},
    ]
    # feed (the recurring trigger) and the startup snapshot branch both flow into guard.
    edges = [
        {"from": "start", "to": "broker"},
        {"from": "broker", "to": "account"}, {"from": "account", "to": "open_orders"},
        {"from": "broker", "to": "feed"},
        {"from": "feed", "to": "guard"}, {"from": "open_orders", "to": "guard"}, {"from": "account", "to": "guard"},
    ]
    graph = {"id": "snap", "name": "Snapshot retention", "nodes": nodes, "edges": edges}
    fixture = {
        "as_of": AS_OF,
        "nodes": {
            "broker": recording("OverseasStockBrokerNode", {}, {"connection": CONN},
                                {"type": "object", "required": ["connection"]}, as_of=AS_OF),
            "account": recording("OverseasStockAccountNode", {"connection": CONN},
                                 {"held_symbols": [], "balance": {"orderable_amount": 1000}, "positions": positions},
                                 {"type": "object", "required": ["balance", "positions"]}, as_of=AS_OF),
            "open_orders": recording("OverseasStockOpenOrdersNode", {"connection": CONN},
                                     {"open_orders": open_rows, "count": len(open_rows)},
                                     {"type": "object", "required": ["open_orders", "count"]}, as_of=AS_OF),
            "feed": _feed_rec(AS_OF, 150),
        },
        "expected": {"guard": {"type": "object", "const": {"allowed": allow}}},
        "must_execute": ["guard"],
        "events": [{"as_of": LATER, "type": "market_data", "source_node_id": "feed",
                    "nodes": {"feed": _feed_rec(LATER, 150)},
                    "must_execute": ["feed", "guard"],
                    "expected": {"guard": {"type": "object", "const": {"allowed": allow}}}}],
    }
    return graph, fixture


@pytest.mark.asyncio
async def test_open_order_snapshot_survives_the_retrigger_and_keeps_the_guard_blocked():
    open_rows = [{"order_id": "OPEN-1", "symbol": "A", "exchange": "NASDAQ", "side": "buy",
                  "order_type": "limit", "quantity": 1, "filled_quantity": 0, "remaining_quantity": 1}]
    graph, fixture = build(open_rows, positions=[])
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    # Blocked initially (open order present) AND still blocked after the tick.
    assert result.outputs["guard"]["allowed"] is False
    assert result.events[0]["outputs"]["guard"]["allowed"] is False
    # The re-trigger re-executed only the tick's downstream chain; the snapshot
    # node was NOT re-executed yet its output remained visible to the guard.
    assert "open_orders" not in result.events[0]["executed"]
    assert result.events[0]["outputs"]["open_orders"]["open_orders"] == open_rows
    check_final_expectations(result, fixture, graph)


@pytest.mark.asyncio
async def test_held_position_snapshot_survives_the_retrigger_and_keeps_the_guard_blocked():
    positions = [{"symbol": "A", "exchange": "NASDAQ", "quantity": 1}]
    graph, fixture = build([], positions=positions)
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["guard"]["allowed"] is False
    assert result.events[0]["outputs"]["guard"]["allowed"] is False
    assert "account" not in result.events[0]["executed"]
    assert result.events[0]["outputs"]["account"]["positions"] == positions
    check_final_expectations(result, fixture, graph)


@pytest.mark.asyncio
async def test_clear_snapshot_allows_on_both_the_initial_run_and_the_retrigger():
    # Control: with no open order and no holding the guard allows both times, so the
    # retention above is a genuine block, not a stuck value.
    graph, fixture = build([], positions=[])
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["guard"]["allowed"] is True
    assert result.events[0]["outputs"]["guard"]["allowed"] is True
    check_final_expectations(result, fixture, graph)

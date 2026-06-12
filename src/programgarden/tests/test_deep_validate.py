"""deep_validate (virtual full-execution) tests.

Covers the Phase 1 contract from the deep-workflow-validation plan:

- Orders are never placed (no broker login, no order send) in deep mode.
- Realtime / data nodes return schema-shaped fixtures so the flow completes
  without waiting for live events (no hang).
- ScheduleNode fires once and the run terminates.
- Strict error collection: a single pass accumulates as many node errors as
  possible (does not abort on the first failure) and reports passed=False.
- Time-boxing: a hanging node still returns within the timeout.
- Zero network: data nodes (Account / MarketData) never call ensure_ls_login.

All tests run with a hard timeout to guarantee no test hangs.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

import programgarden.executor as executor_mod
from programgarden import ProgramGarden
from programgarden.context import ExecutionContext
from programgarden.executor import (
    AccountNodeExecutor,
    BrokerNodeExecutor,
    MarketDataNodeExecutor,
    NewOrderNodeExecutor,
    OpenOrdersNodeExecutor,
    RealAccountNodeExecutor,
    RealMarketDataNodeExecutor,
    RealOrderEventNodeExecutor,
    WorkflowExecutor,
)


pytestmark = pytest.mark.timeout(30)


# ============================================================
# Helpers
# ============================================================

def make_deep_context(job_id: str = "deep-test") -> ExecutionContext:
    ctx = ExecutionContext(
        job_id=job_id,
        workflow_id="wf-deep-test",
        context_params={"deep_validate": True},
    )
    ctx._is_running = True
    return ctx


def _broker_node(node_id: str = "broker", node_type: str = "OverseasStockBrokerNode") -> dict:
    return {"id": node_id, "type": node_type, "credential_id": "cred"}


def _credentials() -> list:
    return [
        {
            "credential_id": "cred",
            "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
            ],
        }
    ]


def order_workflow() -> dict:
    """start → broker → account → new_order (overseas stock)."""
    return {
        "id": "wf-deep-order",
        "name": "deep order workflow",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _broker_node(),
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "new_order",
                "type": "OverseasStockNewOrderNode",
                "config": {
                    "symbol": {"symbol": "AAPL", "exchange": "NASDAQ"},
                    "side": "buy",
                    "quantity": 1,
                    "order_type": "market",
                },
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "new_order"},
        ],
        "credentials": _credentials(),
    }


# ============================================================
# 1. flag propagation
# ============================================================

def test_deep_validate_flag_is_dry_run_superset():
    ctx = make_deep_context()
    assert ctx.is_deep_validate is True
    assert ctx.is_dry_run is True  # superset


def test_plain_dry_run_is_not_deep():
    ctx = ExecutionContext(
        job_id="x", workflow_id="w", context_params={"dry_run": True}
    )
    assert ctx.is_dry_run is True
    assert ctx.is_deep_validate is False


# ============================================================
# 2. Orders are never placed; broker login never happens
# ============================================================

@pytest.mark.asyncio
async def test_order_workflow_places_no_real_order_and_no_login():
    """Deep-validating an order workflow must NOT log into the broker or send
    an order — every order node returns a simulated result."""
    pg = ProgramGarden()

    # If ensure_ls_login is ever called in deep mode, fail loudly.
    def _boom(*args, **kwargs):  # pragma: no cover - asserted via call_count
        raise AssertionError("ensure_ls_login must NOT be called in deep_validate")

    with patch.object(executor_mod, "ensure_ls_login", side_effect=_boom) as mock_login:
        result = await pg.executor.deep_validate(order_workflow(), timeout=12.0)

    assert mock_login.call_count == 0, "broker login must never happen in deep mode"
    assert result.is_valid, [e.short() for e in result.errors]


@pytest.mark.asyncio
async def test_new_order_executor_simulates_in_deep_mode():
    """The order executor itself returns a simulated order (no LS call)."""
    ctx = make_deep_context()
    ex = NewOrderNodeExecutor()
    out = await ex.execute(
        node_id="new_order",
        node_type="OverseasStockNewOrderNode",
        config={"symbol": {"symbol": "AAPL", "exchange": "NASDAQ"}, "side": "buy", "quantity": 1},
        context=ctx,
    )
    assert out.get("status") == "simulated"
    assert str(out.get("order_id", "")).startswith("DRYRUN-")


# ============================================================
# 3. Realtime / data nodes return fixtures (no event wait, no network)
# ============================================================

@pytest.mark.asyncio
async def test_real_market_data_returns_fixture_in_deep_mode():
    ctx = make_deep_context()
    ex = RealMarketDataNodeExecutor()
    out = await ex.execute(
        node_id="rt",
        node_type="OverseasStockRealMarketDataNode",
        config={"symbols": [{"symbol": "TSLA", "exchange": "NASDAQ"}], "connection": {"product": "overseas_stock"}},
        context=ctx,
    )
    assert "ohlcv_data" in out and "data" in out
    assert "TSLA" in out["ohlcv_data"]
    bars = out["ohlcv_data"]["TSLA"]
    assert bars and all(k in bars[0] for k in ("date", "open", "high", "low", "close", "volume"))


@pytest.mark.asyncio
async def test_real_account_returns_fixture_positions_balance():
    ctx = make_deep_context()
    ex = RealAccountNodeExecutor()
    out = await ex.execute(
        node_id="acct",
        node_type="OverseasStockRealAccountNode",
        config={"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "connection": {"product": "overseas_stock"}},
        context=ctx,
    )
    assert isinstance(out.get("positions"), list)
    assert isinstance(out.get("balance"), dict)
    assert "USD" in out["balance"]


@pytest.mark.asyncio
async def test_real_order_event_returns_simulated_fill():
    ctx = make_deep_context()
    ex = RealOrderEventNodeExecutor()
    out = await ex.execute(
        node_id="evt",
        node_type="OverseasStockRealOrderEventNode",
        config={"connection": {"product": "overseas_stock"}},
        context=ctx,
    )
    assert out.get("status") == "체결"
    assert "filled" in out and out["filled"].get("status") == "체결"


@pytest.mark.asyncio
async def test_account_node_fixture_no_login():
    """AccountNode (REST) had no dry_run guard — verify deep injects a fixture
    and never calls ensure_ls_login."""
    ctx = make_deep_context()
    ex = AccountNodeExecutor()
    with patch.object(executor_mod, "ensure_ls_login") as mock_login:
        out = await ex.execute(
            node_id="account",
            node_type="OverseasStockAccountNode",
            config={"connection": {"product": "overseas_stock"}},
            context=ctx,
        )
    assert mock_login.call_count == 0
    assert isinstance(out.get("positions"), list)
    assert isinstance(out.get("balance"), dict)


@pytest.mark.asyncio
async def test_market_data_node_fixture_no_login():
    ctx = make_deep_context()
    ex = MarketDataNodeExecutor()
    with patch.object(executor_mod, "ensure_ls_login") as mock_login:
        out = await ex.execute(
            node_id="md",
            node_type="OverseasStockMarketDataNode",
            config={"symbols": [{"symbol": "NVDA", "exchange": "NASDAQ"}], "connection": {"product": "overseas_stock"}},
            context=ctx,
        )
    assert mock_login.call_count == 0
    assert isinstance(out.get("values"), list) and out["values"]
    assert out["values"][0]["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_open_orders_fixture_no_network():
    ctx = make_deep_context()
    ex = OpenOrdersNodeExecutor()
    with patch.object(executor_mod, "ensure_ls_login") as mock_login:
        out = await ex.execute(
            node_id="oo",
            node_type="OverseasStockOpenOrdersNode",
            config={"connection": {"product": "overseas_stock"}},
            context=ctx,
        )
    assert mock_login.call_count == 0
    assert out.get("open_orders") == [] and out.get("count") == 0


@pytest.mark.asyncio
async def test_broker_node_fixture_connection_no_login():
    """BrokerNode deep returns a fixture connection without login/credential
    injection or fill-price sync (no network)."""
    ctx = make_deep_context()
    ex = BrokerNodeExecutor()
    with patch.object(executor_mod, "ensure_ls_login") as mock_login:
        out = await ex.execute(
            node_id="broker",
            node_type="OverseasStockBrokerNode",
            config={"credential_id": "cred", "product": "overseas_stock"},
            context=ctx,
        )
    assert mock_login.call_count == 0
    assert out.get("connected") is True
    assert out["connection"]["product"] == "overseas_stock"


# ============================================================
# 4. Fixture override
# ============================================================

@pytest.mark.asyncio
async def test_fixture_override_is_applied():
    ctx = ExecutionContext(
        job_id="ovr",
        workflow_id="w",
        context_params={
            "deep_validate": True,
            "deep_fixtures": {"md": {"values": [{"symbol": "ZZZ", "price": 999.0}]}},
        },
    )
    ctx._is_running = True
    ex = MarketDataNodeExecutor()
    out = await ex.execute(
        node_id="md",
        node_type="OverseasStockMarketDataNode",
        config={"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "connection": {"product": "overseas_stock"}},
        context=ctx,
    )
    assert out["values"] == [{"symbol": "ZZZ", "price": 999.0}]


# ============================================================
# 5. End-to-end entry: realtime / schedule workflows complete
# ============================================================

@pytest.mark.asyncio
async def test_realtime_workflow_completes_without_event_wait():
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-realtime",
        "name": "deep realtime",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _broker_node(),
            {"id": "watchlist", "type": "WatchlistNode", "config": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}},
            {"id": "realtime", "type": "OverseasStockRealMarketDataNode", "config": {}},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "realtime"},
        ],
        "credentials": _credentials(),
    }
    result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=12.0), timeout=20.0)
    assert result.is_valid, [e.short() for e in result.errors]


@pytest.mark.asyncio
async def test_schedule_workflow_fires_once_and_terminates():
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-sched",
        "name": "deep schedule",
        "nodes": [
            {"id": "sched", "type": "ScheduleNode", "config": {"cron": "0 9 * * *", "enabled": True}},
            {"id": "start", "type": "StartNode"},
        ],
        "edges": [{"from": "sched", "to": "start"}],
    }
    result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=10.0), timeout=18.0)
    assert result.is_valid, [e.short() for e in result.errors]


# ============================================================
# 6. Strict error collection (accumulate, do not abort on first failure)
# ============================================================

@pytest.mark.asyncio
async def test_deep_collects_multiple_node_errors_without_aborting():
    """Two independent nodes both raise → both surface in errors, and passed is
    False. This proves the deep pass keeps going after the first failure."""
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-multierr",
        "name": "deep multi error",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "a", "type": "WatchlistNode", "config": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}},
            {"id": "b", "type": "WatchlistNode", "config": {"symbols": [{"symbol": "TSLA", "exchange": "NASDAQ"}]}},
        ],
        "edges": [
            {"from": "start", "to": "a"},
            {"from": "start", "to": "b"},
        ],
        "credentials": [],
    }

    real_execute_node = WorkflowExecutor.execute_node

    async def failing_execute_node(self, *, node_id, node_type, **kwargs):
        if node_id in ("a", "b"):
            raise RuntimeError(f"boom-{node_id}")
        return await real_execute_node(self, node_id=node_id, node_type=node_type, **kwargs)

    with patch.object(WorkflowExecutor, "execute_node", failing_execute_node):
        result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=10.0), timeout=18.0)

    assert not result.is_valid
    failed_nodes = {e.location.node_id for e in result.errors if e.location.node_id}
    assert {"a", "b"} <= failed_nodes, f"expected both a and b in {failed_nodes}"
    # deep errors use the dedicated code with a stage detail
    deep_errs = [e for e in result.errors if e.code == "DEEP_VALIDATION_NODE_ERROR"]
    assert len(deep_errs) >= 2
    assert all(e.details.get("stage") == "node_execution" for e in deep_errs)


@pytest.mark.asyncio
async def test_deep_reports_static_structure_errors_without_raising():
    """A definition that fails static schema validation returns a result (never
    raises) carrying the structure errors."""
    pg = ProgramGarden()
    bad = {"workflow_id": "no_id_or_name", "nodes": [], "edges": []}
    result = await asyncio.wait_for(pg.executor.deep_validate(bad, timeout=5.0), timeout=10.0)
    assert not result.is_valid
    assert result.errors  # structure errors surfaced, no exception


# ============================================================
# 7. Time-boxing: a hanging node still returns within timeout
# ============================================================

@pytest.mark.asyncio
async def test_deep_returns_within_timeout_on_hang():
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-hang",
        "name": "deep hang",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "slow", "type": "WatchlistNode", "config": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}},
        ],
        "edges": [{"from": "start", "to": "slow"}],
        "credentials": [],
    }

    real_execute_node = WorkflowExecutor.execute_node

    async def hanging_execute_node(self, *, node_id, node_type, **kwargs):
        if node_id == "slow":
            await asyncio.sleep(60)  # would hang far past the timeout
        return await real_execute_node(self, node_id=node_id, node_type=node_type, **kwargs)

    loop = asyncio.get_event_loop()
    t0 = loop.time()
    with patch.object(WorkflowExecutor, "execute_node", hanging_execute_node):
        result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=2.0), timeout=12.0)
    elapsed = loop.time() - t0

    assert elapsed < 10.0, f"deep_validate should return near the 2s timeout, took {elapsed:.1f}s"
    assert not result.is_valid
    assert any(e.code == "DEEP_VALIDATION_FLOW_BROKEN" for e in result.errors)


# ============================================================
# 8. client.validate_deep (sync wrapper)
# ============================================================

def test_client_validate_deep_sync_wrapper():
    pg = ProgramGarden()
    result = pg.validate_deep(order_workflow(), timeout=12.0)
    assert result.is_valid, [e.short() for e in result.errors]


# ============================================================
# 9. Phase 1.5 — faithful fixtures (schema-mirrored, sufficient OHLCV)
# ============================================================

def test_historical_fixture_mirrors_real_output_schema():
    """HistoricalDataNode real output is {value, values, symbols} where each
    entry is {symbol, exchange, time_series:[bars]} — NOT an ohlcv_data map.
    A faithful fixture must mirror that so the downstream ConditionNode (which
    auto-iterates `values` and reads `item.time_series`) sees the runtime shape.
    """
    from programgarden import deep_fixtures as df

    fx = df.historical_data_fixture(
        {"period": "1d"}, [{"symbol": "AAPL", "exchange": "NASDAQ"}]
    )
    assert set(fx) >= {"value", "values", "symbols"}
    assert fx["value"] is not None  # single symbol → populated value port
    assert isinstance(fx["values"], list) and fx["values"]
    entry = fx["values"][0]
    assert set(entry) >= {"symbol", "exchange", "time_series"}
    assert entry["symbol"] == "AAPL"
    bars = entry["time_series"]
    assert all(k in bars[0] for k in ("date", "open", "high", "low", "close", "volume"))


def test_historical_fixture_has_enough_bars_for_rsi():
    """The series must be long enough that RSI(14)/Bollinger(20) compute a real
    value rather than a 'data too short' sentinel (Phase 1 false-positive root)."""
    from programgarden import deep_fixtures as df

    fx = df.historical_data_fixture({}, [{"symbol": "AAPL", "exchange": "NASDAQ"}])
    bars = fx["values"][0]["time_series"]
    assert len(bars) >= 30, f"need >=30 bars for indicator computation, got {len(bars)}"


def test_account_fixture_has_a_losing_position():
    """At least one held position must be underwater so per-position stop-loss
    conditions actually trigger during a deep run (else the risk branch is never
    exercised — a false negative)."""
    from programgarden import deep_fixtures as df

    positions = df._fixture_positions(
        {}, [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "TSLA", "exchange": "NASDAQ"}]
    )
    assert any(p["pnl_rate"] < 0 for p in positions), "expected a losing position"


# ============================================================
# 10. Phase 1.5 — ConditionNode / SymbolFilter deep flow guarantee
# ============================================================

@pytest.mark.asyncio
async def test_condition_node_passes_input_symbols_in_deep_mode():
    """A signal gate in deep mode must let at least its input symbols through so
    the downstream sizing/order/notify branch (and its {{ item.* }} bindings) is
    exercised regardless of whether the fixture series fires the indicator."""
    from programgarden.executor import ConditionNodeExecutor

    ctx = make_deep_context()
    # Seed a historical-shaped input the ConditionNode RSI plugin can read.
    from programgarden import deep_fixtures as df
    hist = df.historical_data_fixture({}, [{"symbol": "AAPL", "exchange": "NASDAQ"}])
    ctx.set_output("hist", "values", hist["values"])
    ctx.set_iteration_context(hist["values"][0], 0, 1)

    ex = ConditionNodeExecutor()
    out = await ex.execute(
        node_id="rsi",
        node_type="ConditionNode",
        config={
            "plugin": "RSI",
            "items": {
                "from": "{{ item.time_series }}",
                "extract": {
                    "symbol": "{{ item.symbol }}",
                    "exchange": "{{ item.exchange }}",
                    "date": "{{ row.date }}",
                    "close": "{{ row.close }}",
                },
            },
            "fields": {"period": 14, "threshold": 30, "direction": "above"},
        },
        context=ctx,
        fields={"period": 14, "threshold": 30, "direction": "above"},
    )
    # direction=above on a declining-tail series would normally fail; deep mode
    # guarantees the input symbols flow through anyway.
    assert out.get("passed_symbols"), "deep mode should pass input symbols through"
    assert out.get("result") is True


@pytest.mark.asyncio
async def test_symbol_filter_falls_back_to_input_a_in_deep_mode():
    """A difference that empties out (all candidates already held) must not gate
    the downstream branch in deep mode — fall back to input_a."""
    from programgarden.executor import SymbolFilterNodeExecutor

    ctx = make_deep_context()
    ex = SymbolFilterNodeExecutor()
    held = [{"symbol": "AAPL", "exchange": "NASDAQ"}]
    out = await ex.execute(
        node_id="filter",
        node_type="SymbolFilterNode",
        config={"operation": "difference", "input_a": held, "input_b": held},
        context=ctx,
    )
    assert out["symbols"], "deep mode should not leave the filter empty"
    assert out["symbols"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_symbol_filter_keeps_real_result_in_dry_run():
    """The fallback is deep-only — plain dry_run keeps the exact set-op result."""
    from programgarden.executor import SymbolFilterNodeExecutor

    ctx = ExecutionContext(job_id="x", workflow_id="w", context_params={"dry_run": True})
    ctx._is_running = True
    ex = SymbolFilterNodeExecutor()
    held = [{"symbol": "AAPL", "exchange": "NASDAQ"}]
    out = await ex.execute(
        node_id="filter",
        node_type="SymbolFilterNode",
        config={"operation": "difference", "input_a": held, "input_b": held},
        context=ctx,
    )
    assert out["symbols"] == [], "dry_run must keep the empty difference result"


# ============================================================
# 11. Phase 1.5 — unresolved binding promotion
# ============================================================

def test_unresolved_binding_recorded_only_in_deep_mode():
    deep = make_deep_context()
    deep.record_deep_unresolved_binding("n", "{{ item.x }}", "undefined")
    assert deep.get_deep_unresolved_bindings() == [
        {"node_id": "n", "expression": "{{ item.x }}", "reason": "undefined"}
    ]
    # dedup on (node, expression)
    deep.record_deep_unresolved_binding("n", "{{ item.x }}", "undefined again")
    assert len(deep.get_deep_unresolved_bindings()) == 1

    dry = ExecutionContext(job_id="x", workflow_id="w", context_params={"dry_run": True})
    dry.record_deep_unresolved_binding("n", "{{ item.x }}", "undefined")
    assert dry.get_deep_unresolved_bindings() == [], "no-op outside deep mode"


@pytest.mark.asyncio
async def test_unresolved_item_binding_blocks_deep_validate():
    """An IfNode using `{{ item.pnl_rate }}` (which never resolves at runtime —
    IfNode has no iteration context) must be flagged as a blocking
    DEEP_VALIDATION_BINDING_UNRESOLVED error, not silently pass."""
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-item-bug",
        "name": "if-node item anti-pattern",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _broker_node(),
            {"id": "account", "type": "OverseasStockAccountNode"},
            {"id": "gate", "type": "IfNode", "left": "{{ item.pnl_rate }}", "operator": "<=", "right": -5},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "gate"},
        ],
        "credentials": _credentials(),
    }
    result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=12.0), timeout=20.0)
    assert not result.is_valid
    binding_errs = [e for e in result.errors if e.code == "DEEP_VALIDATION_BINDING_UNRESOLVED"]
    assert binding_errs, [e.short() for e in result.errors]
    assert "item" in binding_errs[0].message


@pytest.mark.asyncio
async def test_faithful_workflow_passes_deep_validate():
    """A correctly-wired multi-symbol workflow (watchlist → market → sizing with
    sizing auto-iterating) passes deep_validate with the faithful fixtures."""
    pg = ProgramGarden()
    wf = {
        "id": "wf-deep-faithful",
        "name": "faithful sizing",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _broker_node(),
            {"id": "account", "type": "OverseasStockAccountNode"},
            {"id": "watchlist", "type": "WatchlistNode", "config": {"symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]}},
            {"id": "market", "type": "OverseasStockMarketDataNode"},
            {
                "id": "sizing",
                "type": "PositionSizingNode",
                "symbol": "{{ item }}",
                "balance": "{{ nodes.account.balance.orderable_amount }}",
                "market_data": "{{ nodes.market.value }}",
                "method": "fixed_percent",
                "max_percent": 10.0,
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "watchlist", "to": "market"},
            {"from": "account", "to": "sizing"},
            {"from": "market", "to": "sizing"},
        ],
        "credentials": _credentials(),
    }
    result = await asyncio.wait_for(pg.executor.deep_validate(wf, timeout=12.0), timeout=20.0)
    assert result.is_valid, [e.short() for e in result.errors]


# ============================================================
# 12. Phase 1.5 — auto-iterate pacing skipped in deep mode (timebox)
# ============================================================

@pytest.mark.asyncio
async def test_auto_iterate_pacing_skipped_in_deep_mode():
    """The per-item rate-limit pacing models a real broker API limit; in deep
    mode (no real calls) it must be skipped so a wide watchlist does not blow the
    timebox."""
    ctx = make_deep_context()
    ex = WorkflowExecutor()
    job = WorkflowExecutor.__new__(WorkflowExecutor)  # not needed; use a job-bound sleep check

    # Build a minimal job that carries the deep context and call the pacing helper.
    from programgarden.executor import WorkflowJob
    job = WorkflowJob.__new__(WorkflowJob)
    job.context = ctx
    slept = []

    import programgarden.executor as exmod
    orig_sleep = asyncio.sleep

    async def spy_sleep(d, *a, **k):
        slept.append(d)
        return await orig_sleep(0)

    with patch.object(exmod.asyncio, "sleep", spy_sleep):
        # Even a node type that has a rate limit must not sleep in deep mode.
        await WorkflowJob._auto_iterate_pacing_sleep(job, "new_order", "OverseasStockNewOrderNode")
    assert slept == [], "deep mode must not pace-sleep"


# ============================================================
# 13. Phase 1.5 — Pydantic field/type error promotion (deep only)
# ============================================================

@pytest.mark.asyncio
async def test_generic_node_invalid_config_raises_in_deep_mode():
    """GenericNodeExecutor: a Pydantic construction failure (bad/extra field)
    must RAISE in deep mode so the main loop captures a blocking node error,
    rather than returning a silent {"error": ...} output that marks the node
    completed and hides the defect from deep_validate."""
    from programgarden.executor import GenericNodeExecutor

    ctx = make_deep_context()
    ex = GenericNodeExecutor()
    # SQLiteNode.query expects a string; an int fails Pydantic construction.
    with pytest.raises(Exception):
        await ex.execute(
            node_id="sql",
            node_type="SQLiteNode",
            config={"query": 123},
            context=ctx,
        )


@pytest.mark.asyncio
async def test_generic_node_invalid_config_lenient_in_dry_run():
    """The raise is deep-only — plain dry_run keeps the lenient {"error": ...}
    output so existing mocked validation flows are unaffected."""
    from programgarden.executor import GenericNodeExecutor

    ctx = ExecutionContext(job_id="x", workflow_id="w", context_params={"dry_run": True})
    ctx._is_running = True
    ex = GenericNodeExecutor()
    out = await ex.execute(
        node_id="sql",
        node_type="SQLiteNode",
        config={"query": 123},
        context=ctx,
    )
    assert isinstance(out, dict)
    assert "error" in out, "dry_run must keep lenient error output"

"""Retained personal execution evidence using synthetic SQLite fills only."""
from types import SimpleNamespace
import sqlite3

import pytest

from programgarden.context import ExecutionContext
from programgarden.database import WorkflowPositionTracker


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket
    def denied(*args, **kwargs):
        raise AssertionError("Personal metrics tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


def tracker(tmp_path, **kwargs):
    return WorkflowPositionTracker(str(tmp_path / "workflow.db"), "job", "broker", **kwargs)


async def fill(ledger, order, side, quantity, price, execution, *, symbol="SYNTH", manual=False, date="20260909"):
    if not manual:
        ledger.record_order(order, date, symbol, "SYNTH_EXCHANGE", side, quantity, price, "job", "node")
    return await ledger.record_fill(order, date, symbol, "SYNTH_EXCHANGE", side,
                                   quantity, price, "100000000", "10" if manual else "40", execution_id=execution)


@pytest.mark.asyncio
async def test_flat_position_retains_realized_pnl_in_actual_listener(tmp_path):
    ledger = tracker(tmp_path, provider="ls-sec.co.kr")
    await fill(ledger, "001", "buy", 1, 100, "11")
    await fill(ledger, "002", "sell", 1, 110, "12")
    events = []
    async def observe(event):
        events.append(event)
    context = ExecutionContext(job_id="job", workflow_id="workflow")
    context._workflow_position_tracker = ledger
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    await context.notify_workflow_pnl("broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    event = events[0]
    assert event.workflow_pnl_amount == 0
    assert event.personal_metrics["executed_order_count"] == 2
    assert event.personal_metrics["realized_pnl"][0]["amount"] == 10
    assert event.personal_metrics["realized_pnl"][0]["currency"] is None
    assert event.personal_metrics["max_drawdown"] is None
    assert event.personal_metrics["basis"] == "stored_fifo_gross_excluding_fees"


@pytest.mark.asyncio
async def test_price_ticks_reuse_actual_observation_until_refresh_without_crossing_scope(tmp_path, monkeypatch):
    ledger = tracker(tmp_path, provider="ls-sec.co.kr")
    context = ExecutionContext(job_id="job", workflow_id="workflow")
    context._workflow_position_tracker = ledger
    events = []
    async def observe(event):
        events.append(event)
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    clock = [100.0]
    monkeypatch.setattr("programgarden.context.time.monotonic", lambda: clock[0])
    await context.notify_workflow_pnl("broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    before = events[-1].personal_metrics
    # 체결이 없는 가격 틱은 원장을 읽지 않고 그대로 재사용한다(캐시의 본래 목적).
    clock[0] += 1
    await context.notify_workflow_pnl("broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    assert events[-1].personal_metrics == before
    assert events[-1].personal_metrics["as_of"] == before["as_of"]
    # 🔴 체결은 다르다 — 10초 창이 남아 있어도 즉시 반영돼야 한다.
    # 실측 2026-09-10: SNDL 실체결이 원장에 들어간 0.5초 전에 계산된 봉투가 그대로
    # 저장돼, 원장에 체결 1건이 있는데 체결 주문 수가 0 으로 남았다. 원샷 워크플로우는
    # 곧바로 끝나 "10초 뒤 갱신"이 영영 오지 않는다.
    await fill(ledger, "1", "buy", 1, 100, "11")
    clock[0] += 1
    await context.notify_workflow_pnl("broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    assert events[-1].personal_metrics["executed_order_count"] == 1
    assert events[-1].personal_metrics["as_of"] != before["as_of"]
    await context.notify_workflow_pnl("other-broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    assert events[-1].personal_metrics is None
    context._workflow_position_tracker = tracker(tmp_path, provider="ls-sec.co.kr", trading_mode="paper")
    await context.notify_workflow_pnl("broker", "overseas_stock", "ls-sec.co.kr", {}, {})
    assert events[-1].personal_metrics["scope"]["trading_mode"] == "paper"
    assert events[-1].personal_metrics["executed_order_count"] == 0


@pytest.mark.asyncio
async def test_futures_count_is_unavailable_while_an_app_session_owns_reconciliation(tmp_path):
    # With a lifecycle handler attached, executor.on_tc3_event stops feeding
    # fills into the ledger, so its 0 means "not counted here", not "none".
    ledger = tracker(tmp_path, product="overseas_futures", provider="ls-sec.co.kr")
    events = []
    async def observe(event):
        events.append(event)
    context = ExecutionContext(job_id="job", workflow_id="workflow",
                               order_lifecycle_handler=SimpleNamespace())
    context._workflow_position_tracker = ledger
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    await context.notify_workflow_pnl("broker", "overseas_futures", "ls-sec.co.kr", {}, {})
    metrics = events[-1].personal_metrics
    assert metrics["executed_order_count"] is None
    assert metrics["executed_order_count_status"] == "unavailable"
    assert metrics["executed_order_count_reason"] == "local_futures_ledger_not_execution_source"
    # The ledger itself keeps reporting what it holds; only the envelope is honest.
    assert ledger.personal_metrics()["executed_order_count_status"] == "available"


@pytest.mark.asyncio
async def test_futures_without_an_app_session_and_stock_with_one_keep_their_counts(tmp_path):
    events = []
    async def observe(event):
        events.append(event)
    async def emit(context, product, ledger):
        context._workflow_position_tracker = ledger
        context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
        await context.notify_workflow_pnl("broker", product, "ls-sec.co.kr", {}, {})
        return events[-1].personal_metrics

    futures = tracker(tmp_path / "a", product="overseas_futures", provider="ls-sec.co.kr")
    await fill(futures, "001", "buy", 1, 100, "11", symbol="FUT")
    solo = await emit(ExecutionContext(job_id="job", workflow_id="workflow"), "overseas_futures", futures)
    assert solo["executed_order_count"] == 1 and solo["executed_order_count_status"] == "available"

    stock = tracker(tmp_path / "b", provider="ls-sec.co.kr")
    await fill(stock, "001", "buy", 1, 100, "11")
    attended = await emit(ExecutionContext(job_id="job", workflow_id="workflow",
                                           order_lifecycle_handler=SimpleNamespace()),
                          "overseas_stock", stock)
    assert attended["executed_order_count"] == 1 and attended["executed_order_count_status"] == "available"


@pytest.mark.asyncio
async def test_partial_fills_exact_replay_and_restart_do_not_inflate_order_count(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "001", "buy", 1, 100, "11")
    await fill(ledger, "1", "buy", 2, 100, "12")
    await fill(ledger, "001", "buy", 1, 100, "11")
    assert ledger.personal_metrics()["executed_order_count"] == 1
    assert tracker(tmp_path).personal_metrics()["executed_order_count"] == 1
    await fill(ledger, "001", "buy", 1, 100, "13", date="20260910")
    assert ledger.personal_metrics()["executed_order_count"] == 2


@pytest.mark.asyncio
async def test_unfilled_manual_other_product_provider_and_mode_do_not_count(tmp_path):
    ledger = tracker(tmp_path)
    ledger.record_order("1", "20260909", "UNFILLED", "SYNTH_EXCHANGE", "buy", 1, 100, "job", "node")
    await fill(ledger, "2", "buy", 1, 100, "11", manual=True)
    await fill(tracker(tmp_path, product="overseas_futures"), "3", "buy", 1, 100, "12", symbol="FUT")
    await fill(tracker(tmp_path, provider="other"), "4", "buy", 1, 100, "13", symbol="OTHER")
    await fill(tracker(tmp_path, trading_mode="paper"), "5", "buy", 1, 100, "14", symbol="PAPER")
    assert ledger.personal_metrics()["executed_order_count"] == 0
    assert ledger.personal_metrics()["executed_order_count_status"] == "available"


@pytest.mark.asyncio
async def test_missing_order_identity_is_unavailable(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")
    with sqlite3.connect(ledger.db_path) as conn:
        conn.execute("UPDATE trade_history SET order_date=NULL")
    result = ledger.personal_metrics()
    assert result["executed_order_count"] is None
    assert result["executed_order_count_status"] == "unavailable"


@pytest.mark.asyncio
async def test_manual_fifo_basis_never_becomes_workflow_realized_money(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11", manual=True)
    await fill(ledger, "2", "sell", 1, 110, "12")
    result = ledger.personal_metrics()
    assert result["executed_order_count"] == 1
    assert result["realized_pnl"][0]["amount"] is None
    assert result["realized_pnl"][0]["reason"] == "mixed_fifo_ownership"


@pytest.mark.asyncio
async def test_unmatched_sell_is_not_a_realized_zero(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "sell", 1, 110, "11")
    assert ledger.personal_metrics()["realized_pnl"][0]["amount"] is None


@pytest.mark.asyncio
async def test_futures_count_does_not_promote_long_only_fifo_to_money(tmp_path):
    ledger = tracker(tmp_path, product="overseas_futures", trading_mode="paper")
    await fill(ledger, "1", "buy", 1, 100, "11")
    await fill(ledger, "2", "sell", 1, 110, "12")
    result = ledger.personal_metrics()
    assert result["executed_order_count"] == 2
    assert result["realized_pnl"][0]["amount"] is None
    assert result["realized_pnl"][0]["reason"] == "futures_fifo_not_monetary"
    assert result["scope"]["trading_mode"] == "paper"


@pytest.mark.asyncio
async def test_nonfinite_history_and_inconsistent_realized_value_remain_unavailable(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")
    await fill(ledger, "2", "sell", 1, 110, "12")
    with sqlite3.connect(ledger.db_path) as conn:
        conn.execute("UPDATE trade_history SET realized_pnl=999 WHERE side='sell'")
    assert ledger.personal_metrics()["realized_pnl"][0]["amount"] is None
    with sqlite3.connect(ledger.db_path) as conn:
        conn.execute("UPDATE trade_history SET quantity=? WHERE side='buy'", (float("inf"),))
    result = ledger.personal_metrics()
    assert result["executed_order_count"] is None
    assert result["realized_pnl"][0]["amount"] is None

"""Retained personal execution evidence using synthetic SQLite fills only."""
from types import SimpleNamespace
import asyncio
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
    # A workflow sell now consumes only workflow lots, so it never realizes the
    # manual buy's basis (no account_avg_price was supplied, so no estimate
    # either). The residual with no estimate is rejected as an incomplete basis.
    assert result["realized_pnl"][0]["reason"] == "incomplete_fifo_basis"


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


# --- v2: closed-trade outcomes -------------------------------------------
# One closed trade = one sell fill, scored from its *stored* realized amount.
# Counts aggregate across symbols (a count has no currency); gross amounts do
# not, so the ratio is published only when one group carries the whole ledger.


@pytest.mark.asyncio
async def test_closed_trades_are_scored_from_the_stored_amount(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 3, 100, "11")
    await fill(ledger, "2", "sell", 1, 110, "12")   # +10
    await fill(ledger, "3", "sell", 1, 90, "13")    # -10
    await fill(ledger, "4", "sell", 1, 100, "14")   # 0
    result = ledger.personal_metrics()
    assert result["version"] == 2
    assert result["closed_trade_count"] == 3
    assert result["winning_trade_count"] == 1
    assert result["losing_trade_count"] == 1
    assert result["breakeven_trade_count"] == 1
    assert result["closed_trade_status"] == "available"
    group = result["realized_pnl"][0]
    assert group["gross_profit"] == 10 and group["gross_loss"] == 10
    assert result["profit_loss_ratio"] == 1.0
    assert result["profit_loss_ratio_status"] == "available"


@pytest.mark.asyncio
async def test_open_position_has_no_closed_trade(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")
    result = ledger.personal_metrics()
    assert result["closed_trade_count"] == 0
    assert result["closed_trade_status"] == "available"
    # Nothing has been closed, so there is no ratio to speak of — and saying so
    # is different from saying the ratio is zero.
    assert result["profit_loss_ratio"] is None
    assert result["profit_loss_ratio_reason"] == "no_closed_trades"


@pytest.mark.asyncio
async def test_winning_only_ledger_does_not_publish_profit_as_a_ratio(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")
    await fill(ledger, "2", "sell", 1, 130, "12")
    result = ledger.personal_metrics()
    assert result["winning_trade_count"] == 1 and result["losing_trade_count"] == 0
    assert result["realized_pnl"][0]["gross_profit"] == 30
    # The server's day-based metric returns gross profit here and the screen
    # reads it as "ratio 30.00". No denominator means no ratio.
    assert result["profit_loss_ratio"] is None
    assert result["profit_loss_ratio_reason"] == "no_losing_trades"


@pytest.mark.asyncio
async def test_two_symbols_count_together_but_publish_no_ratio(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11", symbol="AAA")
    await fill(ledger, "2", "sell", 1, 110, "12", symbol="AAA")
    await fill(ledger, "3", "buy", 1, 200, "13", symbol="BBB")
    await fill(ledger, "4", "sell", 1, 180, "14", symbol="BBB")
    result = ledger.personal_metrics()
    assert result["closed_trade_count"] == 2
    assert result["winning_trade_count"] == 1 and result["losing_trade_count"] == 1
    # Two symbols may settle in two currencies, and the ledger holds no currency
    # evidence — so the amounts stay in their groups.
    assert result["profit_loss_ratio"] is None
    assert result["profit_loss_ratio_reason"] == "multi_symbol_currency_unknown"
    assert {g["symbol"] for g in result["realized_pnl"]} == {"AAA", "BBB"}


@pytest.mark.asyncio
async def test_unscorable_group_downgrades_the_total_instead_of_shrinking_it(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11", symbol="AAA")
    await fill(ledger, "2", "sell", 1, 110, "12", symbol="AAA")
    await fill(ledger, "3", "sell", 1, 50, "13", symbol="BBB")   # unmatched
    result = ledger.personal_metrics()
    assert result["closed_trade_count"] == 1
    assert result["closed_trade_status"] == "partial"
    assert result["closed_trade_reason"] == "some_groups_unscorable"
    rejected = [g for g in result["realized_pnl"] if g["symbol"] == "BBB"][0]
    # An unknown group contributes no trades, not zero trades.
    assert rejected["closed_trades"] is None and rejected["gross_profit"] is None


@pytest.mark.asyncio
async def test_futures_ledger_scores_no_trades(tmp_path):
    ledger = tracker(tmp_path, product="overseas_futures", trading_mode="paper")
    await fill(ledger, "1", "buy", 1, 100, "11")
    await fill(ledger, "2", "sell", 1, 110, "12")
    result = ledger.personal_metrics()
    assert result["closed_trade_count"] is None
    assert result["closed_trade_status"] == "unavailable"
    assert result["closed_trade_reason"] == "futures_fifo_not_monetary"
    assert result["profit_loss_ratio"] is None


@pytest.mark.asyncio
async def test_mixed_ownership_keeps_its_trades_out_of_the_count(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11", manual=True)
    await fill(ledger, "2", "sell", 1, 110, "12")
    result = ledger.personal_metrics()
    # The workflow sell consumes only workflow lots, so the manual buy's basis is
    # never claimed; its residual (no estimate) is an incomplete basis, and the
    # rejected group keeps its trades out of the count exactly as before.
    assert result["realized_pnl"][0]["reason"] == "incomplete_fifo_basis"
    assert result["closed_trade_count"] is None
    assert result["closed_trade_status"] == "unavailable"
    assert result["closed_trade_reason"] == "no_scorable_fifo_basis"


# --- v2 확장: 계좌 평균매입가 추정 + off_strategy_fills ------------------------
# 워크플로우 매도가 자기 로트를 다 소진하고도 남는 잔량은, 계좌에 같은 종목을 다른
# 경로로 사둔 것으로 보고 계좌 평균매입가 기준으로 추정 표기한다(basis includes_estimates).


async def sell_with_estimate(ledger, order, quantity, price, execution, account_avg_price,
                             *, symbol="SYNTH", date="20260909"):
    """워크플로우 매도 + 계좌 평균매입가 추정 인자."""
    ledger.record_order(order, date, symbol, "SYNTH_EXCHANGE", "sell", quantity, price, "job", "node")
    return await ledger.record_fill(order, date, symbol, "SYNTH_EXCHANGE", "sell",
                                    quantity, price, "120000000", "40",
                                    execution_id=execution, account_avg_price=account_avg_price)


@pytest.mark.asyncio
async def test_estimated_tail_makes_the_group_estimated(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")           # workflow 매수 1
    await sell_with_estimate(ledger, "2", 3, 110, "12", 105)  # 3 매도, 잔량 2 추정 @105
    result = ledger.personal_metrics()
    group = result["realized_pnl"][0]
    assert group["status"] == "estimated"
    assert group["basis"] == "fifo_with_account_avg_price_estimate"
    assert group["estimated_quantity"] == 2
    # amount = FIFO 매칭분(1 @ +10) + 추정분((110-105)*2 = +10) = 20
    assert group["amount"] == 20
    assert group["closed_trades"] == 1 and group["winning_trades"] == 1
    # 상위: 추정 그룹 1개, 합계 basis 는 includes_estimates
    assert result["estimated_group_count"] == 1
    assert result["closed_trade_status"] == "available"
    assert result["closed_trade_basis"] == "includes_estimates"
    assert result["closed_trade_count"] == 1


@pytest.mark.asyncio
async def test_estimated_group_ratio_basis_includes_estimates(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 2, 100, "11")           # workflow 매수 2
    await fill(ledger, "2", "sell", 1, 90, "12")           # 매도 1 @90 → 손실 -10 (매칭)
    await sell_with_estimate(ledger, "3", 3, 110, "13", 105)  # 매도 3: 매칭 1(+10) + 추정 2(+10)=+20
    result = ledger.personal_metrics()
    group = result["realized_pnl"][0]
    assert group["status"] == "estimated"
    assert group["winning_trades"] == 1 and group["losing_trades"] == 1
    assert group["gross_profit"] == 20 and group["gross_loss"] == 10
    # 한 그룹만 닫힌 거래가 있으니 손익비 발행 — basis 는 includes_estimates
    assert result["profit_loss_ratio"] == 2.0
    assert result["profit_loss_ratio_status"] == "available"
    assert result["profit_loss_ratio_basis"] == "includes_estimates"


@pytest.mark.asyncio
async def test_residual_without_estimate_stays_unavailable(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")   # workflow 매수 1
    # 3 매도인데 workflow 로트 1뿐 + 계좌 평단 미제공 → 추정 없음 → 거부
    ledger.record_order("2", "20260909", "SYNTH", "SYNTH_EXCHANGE", "sell", 3, 110, "job", "node")
    await ledger.record_fill("2", "20260909", "SYNTH", "SYNTH_EXCHANGE", "sell", 3, 110,
                             "120000000", "40", execution_id="12")
    result = ledger.personal_metrics()
    group = result["realized_pnl"][0]
    assert group["status"] == "unavailable"
    assert group["reason"] == "incomplete_fifo_basis"
    assert group["basis"] is None and group["estimated_quantity"] is None
    assert result["closed_trade_status"] == "unavailable"


@pytest.mark.asyncio
async def test_fully_matched_group_basis_is_measured(tmp_path):
    ledger = tracker(tmp_path)
    await fill(ledger, "1", "buy", 1, 100, "11")
    await fill(ledger, "2", "sell", 1, 110, "12")   # 완전 매칭, 추정 없음
    result = ledger.personal_metrics()
    group = result["realized_pnl"][0]
    assert group["status"] == "available"
    assert group["basis"] == "fifo" and group["estimated_quantity"] == 0
    assert result["estimated_group_count"] == 0
    assert result["closed_trade_basis"] == "measured"


@pytest.mark.asyncio
async def test_off_strategy_fills_counts_hts_and_other_api(tmp_path):
    ledger = tracker(tmp_path, provider="ls-sec.co.kr")
    ledger.FILL_BUFFER_TIMEOUT = 0.05
    await fill(ledger, "1", "buy", 1, 100, "11")   # 우리 workflow 체결
    # 사람의 HTS 거래: 실제 비-'40' 매체코드 + 일치 주문 없음 → manual
    await ledger.record_fill("H1", "20260909", "SYNTH", "SYNTH_EXCHANGE", "buy", 1, 90,
                             "100000000", "41", execution_id="21")
    # 타 API 클라이언트: '40' + 일치 주문 없음 → 버퍼 → unknown_api
    r = await ledger.record_fill("A1", "20260909", "SYNTH", "SYNTH_EXCHANGE", "buy", 1, 95,
                                 "100000000", "40", execution_id="22")
    assert r == "pending"
    await asyncio.sleep(0.15)
    off = ledger.personal_metrics()["off_strategy_fills"]
    assert off["status"] == "available"
    assert off["hts"] == 1
    assert off["other_api"] == 1
    assert off["reason"] is None


@pytest.mark.asyncio
async def test_off_strategy_fills_unavailable_for_futures(tmp_path):
    ledger = tracker(tmp_path, product="overseas_futures", trading_mode="paper")
    await fill(ledger, "1", "buy", 1, 100, "11")
    off = ledger.personal_metrics()["off_strategy_fills"]
    assert off["status"] == "unavailable"
    assert off["hts"] is None and off["other_api"] is None
    assert off["reason"] == "futures_fills_have_no_media_code"

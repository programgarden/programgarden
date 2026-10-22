"""체결 재조정 본체 — 놓친 체결을 원장에 넣고, 유령 포지션을 추정으로 보고한다."""
import pytest

from programgarden.database.fill_reconciler import (
    ACCOUNT_UNAVAILABLE,
    reconcile_workflow_fills,
)


class FakeTracker:
    def __init__(self, pending=None, phantoms=None):
        self._pending = pending or []
        self._phantoms = phantoms or []
        self.recorded = []
        self.phantom_args = None

    def get_unconfirmed_workflow_orders(self, *, min_age_seconds, limit):
        return list(self._pending)

    def get_phantom_workflow_positions(self, account_quantities):
        self.phantom_args = account_quantities
        return list(self._phantoms)

    async def record_fill(self, **kwargs):
        self.recorded.append(kwargs)
        return "workflow"


def _order(order_no, date, symbol, side, qty=1):
    return {"order_no": order_no, "order_date": date, "symbol": symbol,
            "exchange": "NYSE", "side": side, "quantity": qty, "price": 1.0}


def _fills(mapping):
    async def _fetch(order_date):
        return mapping.get(order_date, {})
    return _fetch


# ── 주문 갈래 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missed_fill_is_recorded(tmp_path):
    """prod 에서 놓쳤던 NIO 매도 모양."""
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 2, "avg_price": 3.76, "fill_time": "150701"}}}),
        account_positions={"NIO": {"quantity": 2, "avg_price": 4.19}},
    )
    assert rep.recorded_fills == 1
    got = t.recorded[0]
    assert got["order_no"] == "53" and got["symbol"] == "NIO" and got["side"] == "sell"
    assert got["quantity"] == 2 and got["price"] == 3.76


@pytest.mark.asyncio
async def test_account_avg_price_is_passed_for_the_estimate():
    """🔴 이걸 안 넘기면 '자동매매가 사지 않은 물량을 팔았다' 가 추정으로 안 남는다."""
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 2, "avg_price": 3.76}}}),
        account_positions={"NIO": {"quantity": 2, "avg_price": 4.19}},
    )
    assert t.recorded[0]["account_avg_price"] == 4.19


@pytest.mark.asyncio
async def test_absent_from_response_is_not_treated_as_unfilled():
    """조회 실패와 미체결을 구분할 수 없으므로 아무것도 기록하지 않는다."""
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t, fetch_fills_by_date=_fills({}), account_positions={},
    )
    assert t.recorded == []
    assert rep.still_unfilled == 1 and rep.recorded_fills == 0


@pytest.mark.asyncio
async def test_one_broker_call_per_date_not_per_order():
    """앱키당 2초 1회 제한 — 건당 호출하면 예산을 그대로 먹는다."""
    calls = []

    async def _fetch(order_date):
        calls.append(order_date)
        return {"1": {"filled_qty": 1, "avg_price": 10.0},
                "2": {"filled_qty": 1, "avg_price": 11.0},
                "3": {"filled_qty": 1, "avg_price": 12.0}}

    t = FakeTracker(pending=[_order("1", "20260914", "A", "buy"),
                             _order("2", "20260914", "B", "buy"),
                             _order("3", "20260914", "C", "buy")])
    rep = await reconcile_workflow_fills(t, fetch_fills_by_date=_fetch, account_positions={})
    assert calls == ["20260914"]
    assert rep.recorded_fills == 3


@pytest.mark.asyncio
async def test_zero_padded_order_number_still_matches():
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"0000053": {"filled_qty": 2, "avg_price": 3.76}}}),
        account_positions={},
    )
    assert rep.recorded_fills == 1


@pytest.mark.asyncio
async def test_record_failure_does_not_abort_the_rest():
    class Flaky(FakeTracker):
        async def record_fill(self, **kwargs):
            if kwargs["order_no"] == "1":
                raise RuntimeError("boom")
            return await super().record_fill(**kwargs)

    t = Flaky(pending=[_order("1", "20260914", "A", "buy"), _order("2", "20260914", "B", "buy")])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"1": {"filled_qty": 1, "avg_price": 1.0},
                                                 "2": {"filled_qty": 1, "avg_price": 2.0}}}),
        account_positions={},
    )
    assert rep.recorded_fills == 1
    assert any("record_fill_failed[1]" in e for e in rep.errors)


@pytest.mark.asyncio
async def test_broker_query_exception_is_contained():
    async def _boom(order_date):
        raise RuntimeError("network")

    t = FakeTracker(pending=[_order("1", "20260914", "A", "buy")])
    rep = await reconcile_workflow_fills(t, fetch_fills_by_date=_boom, account_positions={})
    assert rep.recorded_fills == 0
    assert any("fill_query_failed" in e for e in rep.errors)


# ── 잔고 갈래 (대칭의 나머지) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_phantom_position_is_reported():
    t = FakeTracker(phantoms=[{"symbol": "MARA", "lot_quantity": 1, "account_quantity": 0,
                               "missing_quantity": 1, "avg_buy_price": 11.78}])
    rep = await reconcile_workflow_fills(
        t, fetch_fills_by_date=_fills({}), account_positions={"NIO": {"quantity": 3, "avg_price": 4.0}},
    )
    assert rep.phantom_positions == 1 and rep.phantom_quantity == 1


@pytest.mark.asyncio
async def test_account_unavailable_skips_the_phantom_branch():
    """🔴 빈 잔고로 간주하면 보유 중인 로트를 전부 '밖에서 팔렸다' 로 기록한다."""
    t = FakeTracker(phantoms=[{"symbol": "MARA", "lot_quantity": 1, "account_quantity": 0,
                               "missing_quantity": 1, "avg_buy_price": 11.78}])
    rep = await reconcile_workflow_fills(
        t, fetch_fills_by_date=_fills({}), account_positions=ACCOUNT_UNAVAILABLE,
    )
    assert rep.skipped_no_account is True
    assert rep.phantom_positions == 0
    assert t.phantom_args is None, "잔고를 모를 땐 유령 조회 자체를 하지 않아야 한다"


@pytest.mark.asyncio
async def test_float_noise_is_not_a_phantom():
    t = FakeTracker(phantoms=[{"symbol": "MARA", "lot_quantity": 1, "account_quantity": 1,
                               "missing_quantity": 1e-9, "avg_buy_price": 11.78}])
    rep = await reconcile_workflow_fills(
        t, fetch_fills_by_date=_fills({}), account_positions={"MARA": {"quantity": 1}},
    )
    assert rep.phantom_positions == 0


@pytest.mark.asyncio
async def test_account_quantities_are_forwarded_to_the_tracker():
    t = FakeTracker()
    await reconcile_workflow_fills(
        t, fetch_fills_by_date=_fills({}),
        account_positions={"MARA": {"quantity": 1, "avg_price": 11.78},
                           "NIO": {"quantity": 3, "avg_price": 4.19}},
    )
    assert t.phantom_args == {"MARA": 1.0, "NIO": 3.0}


# ── 통합: 진짜 트래커에 붙여 원장이 실제로 채워지는지 ──────────────────────
#
# 이게 이번 사고의 본질이다. 가짜 트래커로는 "record_fill 을 불렀다" 까지만 알 수 있고,
# 정작 문제였던 "lot 이 안 생겨 workflow_pnl_rate 가 NULL" 은 확인되지 않는다.

from programgarden.database.workflow_position_tracker import WorkflowPositionTracker


def _real_tracker(tmp_path):
    return WorkflowPositionTracker(
        db_path=str(tmp_path / "wf.db"), job_id="job-1", broker_node_id="broker",
        product="overseas_stock", provider="ls-sec.co.kr", trading_mode="live",
    )


def _record_order(t, order_no, order_date, symbol, side, qty, price):
    import sqlite3
    from datetime import datetime, timedelta
    with sqlite3.connect(t.db_path) as c:
        c.execute(
            """INSERT INTO workflow_orders
               (product, provider, order_no, order_date, symbol, exchange, side,
                quantity, price, job_id, node_id, trading_mode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (t.product, t.provider, order_no, order_date, symbol, "NASDAQ", side,
             qty, price, "job-1", "n1", t.trading_mode,
             (datetime.now() - timedelta(hours=2)).isoformat()),
        )


@pytest.mark.asyncio
async def test_reconcile_actually_creates_a_lot(tmp_path):
    """매수 체결이 재조정되면 로트가 생겨 워크플로우 포지션이 0 에서 벗어난다."""
    t = _real_tracker(tmp_path)
    _record_order(t, "85", "20260911", "MARA", "buy", 1, 11.78)
    assert t.get_workflow_positions() == {}          # 사고 당시 상태

    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260911": {"85": {"filled_qty": 1, "avg_price": 11.78,
                                                        "fill_time": "133000"}}}),
        account_positions={"MARA": {"quantity": 1, "avg_price": 11.78}},
    )
    assert rep.recorded_fills == 1
    positions = t.get_workflow_positions()
    assert "MARA" in positions, "로트가 안 생기면 workflow_pnl_rate 가 계속 NULL 이다"


@pytest.mark.asyncio
async def test_reconcile_is_idempotent_across_cycles(tmp_path):
    """주기마다 도는 태스크다 — 두 번 돌아도 같은 체결이 두 번 들어가면 안 된다."""
    t = _real_tracker(tmp_path)
    _record_order(t, "85", "20260911", "MARA", "buy", 1, 11.78)
    fetch = _fills({"20260911": {"85": {"filled_qty": 1, "avg_price": 11.78, "fill_time": "133000"}}})
    acct = {"MARA": {"quantity": 1, "avg_price": 11.78}}

    first = await reconcile_workflow_fills(t, fetch_fills_by_date=fetch, account_positions=acct)
    second = await reconcile_workflow_fills(t, fetch_fills_by_date=fetch, account_positions=acct)

    assert first.recorded_fills == 1
    assert second.recorded_fills == 0, "이미 원장에 있는 주문을 다시 기록하면 이중 계상된다"
    assert t.get_workflow_positions()["MARA"].quantity == 1


@pytest.mark.asyncio
async def test_sell_without_workflow_buy_records_an_estimate(tmp_path):
    """NIO 케이스 — 자동매매가 사지 않은 물량을 팔았다. 추정으로 남아야 한다."""
    import sqlite3
    t = _real_tracker(tmp_path)
    _record_order(t, "53", "20260914", "NIO", "sell", 2, 3.76)

    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 2, "avg_price": 3.76,
                                                        "fill_time": "150701"}}}),
        account_positions={"NIO": {"quantity": 2, "avg_price": 4.19}},
    )
    assert rep.recorded_fills == 1

    with sqlite3.connect(t.db_path) as c:
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT realized_pnl, unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl "
            "FROM trade_history WHERE order_no='53'"
        ).fetchone()

    assert row["unmatched_qty"] == 2, "자동매매가 사지 않은 수량이 그대로 표시돼야 한다"
    assert row["estimate_basis_price"] == 4.19
    assert row["estimate_source"] == "account_balance_avg_price"
    assert row["estimated_pnl"] == pytest.approx((3.76 - 4.19) * 2)
    assert row["realized_pnl"] == 0, "추정치가 확정 실현손익에 섞이면 안 된다"


# ── 계좌 교체 후 주문번호 충돌 (2026-09-14) ────────────────────────────────
#
# workflow_orders 에는 계좌 컬럼이 없어서, 계좌를 바꿔도 **옛 계좌 주문이 그대로 남는다**.
# 주문번호는 계좌 안에서만 유일하므로, 새 계좌에서 같은 날 같은 번호가 나오면 남의 체결을
# 우리 주문으로 기록하게 된다. 실제로 prod 파드 원장에 옛 계좌 주문 2건이 남아 있다.

@pytest.mark.asyncio
async def test_same_order_number_different_symbol_is_not_recorded():
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 10, "avg_price": 99.0,
                                                        "symbol": "TSLA"}}}),
        account_positions={},
    )
    assert t.recorded == [], "다른 종목의 체결을 우리 주문으로 기록하면 안 된다"
    assert rep.mismatched_symbol == 1
    assert rep.recorded_fills == 0


@pytest.mark.asyncio
async def test_symbol_match_is_case_and_space_insensitive():
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 2, "avg_price": 3.76,
                                                        "symbol": " nio "}}}),
        account_positions={},
    )
    assert rep.recorded_fills == 1, "표기 차이로 정상 체결을 놓치면 안 된다"
    assert rep.mismatched_symbol == 0


@pytest.mark.asyncio
async def test_broker_without_symbol_still_records():
    """응답이 종목을 안 실어 주면 대조할 수 없다 — 종전 동작(기록)을 유지한다."""
    t = FakeTracker(pending=[_order("53", "20260914", "NIO", "sell", 2)])
    rep = await reconcile_workflow_fills(
        t,
        fetch_fills_by_date=_fills({"20260914": {"53": {"filled_qty": 2, "avg_price": 3.76}}}),
        account_positions={},
    )
    assert rep.recorded_fills == 1

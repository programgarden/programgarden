"""체결 재조정의 조회 절반 — 미확정 주문 / 유령 포지션.

배경(2026-09-14 prod 실측): lot·trade_history 는 체결 이벤트로만 생기는데, 접수 직후
인라인 확인 창이 4회 x 2초로 짧아 지정가가 나중에 체결되면 그 사실이 원장에 영영
도착하지 않았다. MARA 매수(09-11)·NIO 매도(09-14) 둘 다 실제 체결됐는데 trade_history
0건·lot 0건이었고, 그 결과 workflow_pnl_rate 가 NULL 로 발행돼 커뮤니티가 통째로 비었다.

대칭의 나머지 절반: 자동매매가 산 종목을 자동매매 밖에서 팔면 lot 이 남아 계좌에 없는
물량을 보유 중으로 계산한다(과대 계상). lot↔잔고 대조가 저장소에 없었다.
"""
from datetime import datetime, timedelta

import pytest

from programgarden.database.workflow_position_tracker import WorkflowPositionTracker


def _tracker(tmp_path):
    return WorkflowPositionTracker(
        db_path=str(tmp_path / "wf.db"),
        job_id="job-1",
        broker_node_id="broker",
        product="overseas_stock",
        provider="ls-sec.co.kr",
        trading_mode="live",
    )


def _add_order(t, order_no, order_date, symbol, side, qty, price, created_at, mode=None):
    import sqlite3
    with sqlite3.connect(t.db_path) as c:
        c.execute(
            """INSERT INTO workflow_orders
               (product, provider, order_no, order_date, symbol, exchange, side,
                quantity, price, job_id, node_id, trading_mode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (t.product, t.provider, order_no, order_date, symbol, "NYSE", side,
             qty, price, "job-1", "n1", mode or t.trading_mode, created_at),
        )


def _add_history(t, order_no, order_date, symbol, side, qty, price):
    import sqlite3
    with sqlite3.connect(t.db_path) as c:
        c.execute(
            """INSERT INTO trade_history
               (product, provider, order_no, order_date, symbol, exchange, side,
                quantity, price, fill_datetime, classification, commda_code,
                realized_pnl, trading_mode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (t.product, t.provider, order_no, order_date, symbol, "NYSE", side,
             qty, price, "2026-09-14T06:07:01", "workflow", "40", 0.0,
             t.trading_mode, datetime.now().isoformat()),
        )


def _add_lot(t, symbol, qty, buy_price, classification="workflow"):
    import sqlite3
    with sqlite3.connect(t.db_path) as c:
        c.execute(
            """INSERT INTO workflow_position_lots
               (product, provider, symbol, exchange, fill_datetime, buy_price,
                original_qty, remaining_qty, classification, order_no, order_date,
                trading_mode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (t.product, t.provider, symbol, "NYSE", "2026-09-11T13:30:00", buy_price,
             qty, qty, classification, "85", "20260911", t.trading_mode,
             datetime.now().isoformat()),
        )


OLD = (datetime.now() - timedelta(hours=2)).isoformat()


# ── 미확정 주문 ────────────────────────────────────────────────────────────

def test_order_without_fill_is_reported(tmp_path):
    """prod 에서 실제로 벌어진 상태 — 주문은 있는데 체결이 원장에 없다."""
    t = _tracker(tmp_path)
    _add_order(t, "85", "20260911", "MARA", "buy", 1, 11.78, OLD)
    _add_order(t, "53", "20260914", "NIO", "sell", 2, 3.76, OLD)
    out = t.get_unconfirmed_workflow_orders()
    assert {o["order_no"] for o in out} == {"85", "53"}


def test_order_with_fill_is_not_reported(tmp_path):
    t = _tracker(tmp_path)
    _add_order(t, "85", "20260911", "MARA", "buy", 1, 11.78, OLD)
    _add_history(t, "85", "20260911", "MARA", "buy", 1, 11.78)
    assert t.get_unconfirmed_workflow_orders() == []


def test_order_number_padding_does_not_create_a_false_positive(tmp_path):
    """원장에 0 패딩된 주문번호로 들어와도 같은 주문으로 본다 — 아니면 중복 기록된다."""
    t = _tracker(tmp_path)
    _add_order(t, "53", "20260914", "NIO", "sell", 2, 3.76, OLD)
    _add_history(t, "0000053", "20260914", "NIO", "sell", 2, 3.76)
    assert t.get_unconfirmed_workflow_orders() == []


def test_fresh_orders_are_held_back(tmp_path):
    """갓 낸 주문은 인라인 확인 창과 겹친다 — 곧바로 재확인하면 이중 계상 위험."""
    t = _tracker(tmp_path)
    _add_order(t, "99", "20260914", "AAPL", "buy", 1, 190.0, datetime.now().isoformat())
    assert t.get_unconfirmed_workflow_orders(min_age_seconds=60) == []
    assert len(t.get_unconfirmed_workflow_orders(min_age_seconds=0)) == 1


def test_other_trading_mode_is_not_mixed_in(tmp_path):
    """모의투자 주문이 실전 재조정 대상에 섞이면 실계좌에 없는 체결을 기록하게 된다."""
    t = _tracker(tmp_path)          # live
    _add_order(t, "85", "20260911", "MARA", "buy", 1, 11.78, OLD, mode="paper")
    assert t.get_unconfirmed_workflow_orders() == []
    _add_order(t, "86", "20260911", "MARA", "buy", 1, 11.78, OLD)   # live
    assert [o["order_no"] for o in t.get_unconfirmed_workflow_orders()] == ["86"]


def test_limit_and_oldest_first(tmp_path):
    t = _tracker(tmp_path)
    for i in range(5):
        _add_order(t, str(100 + i), "20260914", "AAPL", "buy", 1, 1.0,
                   (datetime.now() - timedelta(hours=5 - i)).isoformat())
    out = t.get_unconfirmed_workflow_orders(limit=2)
    assert [o["order_no"] for o in out] == ["100", "101"]


# ── 유령 포지션 (자동매매 밖에서 팔린 것으로 추정) ──────────────────────────

def test_lot_missing_from_account_is_reported(tmp_path):
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 1, 11.78)
    out = t.get_phantom_workflow_positions({"NIO": 3})
    assert len(out) == 1
    assert out[0]["symbol"] == "MARA"
    assert out[0]["missing_quantity"] == 1
    assert out[0]["avg_buy_price"] == 11.78


def test_lot_still_held_is_not_reported(tmp_path):
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 1, 11.78)
    assert t.get_phantom_workflow_positions({"MARA": 1}) == []


def test_partial_outside_sell_reports_only_the_gap(tmp_path):
    """밖에서 일부만 팔렸으면 그 차이만 보고한다."""
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 5, 11.78)
    out = t.get_phantom_workflow_positions({"MARA": 2})
    assert out[0]["missing_quantity"] == 3
    assert out[0]["lot_quantity"] == 5
    assert out[0]["account_quantity"] == 2


def test_account_holding_more_is_not_a_phantom(tmp_path):
    """계좌에 더 많은 건 자동매매 밖 매수 — 유령이 아니다."""
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 1, 11.78)
    assert t.get_phantom_workflow_positions({"MARA": 4}) == []


def test_non_workflow_lots_are_ignored(tmp_path):
    """수기로 산 물량은 전략 포지션이 아니다."""
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 1, 11.78, classification="manual")
    assert t.get_phantom_workflow_positions({}) == []


def test_weighted_average_across_lots(tmp_path):
    t = _tracker(tmp_path)
    _add_lot(t, "MARA", 1, 10.0)
    _add_lot(t, "MARA", 3, 20.0)
    out = t.get_phantom_workflow_positions({})
    assert out[0]["lot_quantity"] == 4
    assert out[0]["avg_buy_price"] == pytest.approx(17.5)

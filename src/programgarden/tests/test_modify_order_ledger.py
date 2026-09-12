"""정정(ModifyOrder) 원장 기록 — 방향은 원 주문에서 **승계**, 못 찾으면 기록 안 함.

배경(회귀 방지):
    정정 후 체결은 브로커가 새로 발급한 주문번호로 온다. 그 번호가 원장에 없으면
    우리 체결이 (order_no, order_date) 대조에 실패해 manual/unknown_api 로
    오분류된다 — 그래서 새 주문번호를 원장에 남긴다.

    다만 **방향(side)을 추측해서는 안 된다.** ModifyOrder 계열 노드 스키마에는
    side 필드가 아예 없어(core/programgarden_core/nodes/order.py:245-263 =
    connection / original_order_id / symbol / exchange) 세 경로 모두 사실상 항상
    "buy" 가 된다. 그 값이 context.record_workflow_order →
    risk_tracker.register_symbol(entry_price=price, qty=quantity) 로 흘러가면
    보유하지도 않은 종목에 롱 HWM 이 생기고, 그 HWM 이 이후 그 종목의 신규 매수를
    drawdown 게이트(check_drawdown_threshold, 기본 10%)로 막는다. 수량만 정정하면
    entry_price=0.0 짜리 HWM 까지 만들어진다.

    그래서 원 주문 원장 행에서 side/symbol/exchange 를 승계하고, 수량/가격도
    0 으로 치환하지 않고 승계하며, 원 주문을 못 찾으면 아예 기록하지 않는다.
    정정은 새 포지션이 아니므로 리스크 트래커 부수효과도 끈다(register_risk=False).

    그리고 **브로커 요청(와이어)과 원장이 갈리면 안 된다.** 승계는 원장에서만
    하고 와이어는 `new_quantity or 0` / `new_price or 0.0` 이던 시기가 있었는데,
    그러면 수량만 정정했을 때 브로커에는 가격 0 이 나가고 원장에는 원가격이
    적힌다. 세 정정 TR 어디에도 '0 = 변경 없음' 규약이 없다 — 오히려
    CSPAT00701 은 OrdPrc 0 에 다른 뜻을 준다(blocks.py:100-107 "Use 0 for market
    orders ('03')"). SDK 예제도 셋 다 실제 값을 싣는다
    (run_COSAT00311.py:36-37 / run_CIDBT00900.py:39-41 / run_CSPAT00701.py:32-35).
    노드 스키마의 약속도 같다 — nodes/order.py:766-772 "변경하지 않으면 기존 수량
    유지". 그래서 와이어도 실효값(원값 승계)을 싣는다.

    해외선물(CIDBT00900)만은 요청에 **매매구분(BnsTpCode)** 이 들어간다
    (blocks.py:88-93 "'1' = sell, '2' = buy"). 원 주문을 못 찾아 방향을 모르면
    추측하지 않고 **정정 요청 자체를 거른다**(브로커에 아무것도 보내지 않는다).
    ⚠️ LS 가 불일치 BnsTpCode 를 어떻게 처리하는지는 **미관측**이다 — 고치는
    근거는 그 값이 존재할 수 없는 config 키에서 왔다는 사실뿐이다.

라이브 키 없이 mock LS 응답 + 실제 SQLite 원장으로 3개 정정 경로를 모두 검증한다.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
from programgarden.executor import ModifyOrderNodeExecutor


TODAY = datetime.now().strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_context(tmp_path, product):
    """실제 ExecutionContext + 실제 SQLite 원장 + mock 리스크 트래커."""
    ctx = ExecutionContext(job_id="modify-ledger", workflow_id="offline")
    tracker = WorkflowPositionTracker(
        str(tmp_path / f"{product}.sqlite"), ctx.job_id, "broker", product=product
    )
    ctx._workflow_position_tracker = tracker
    ctx._workflow_risk_tracker = MagicMock()
    return ctx, tracker


def _ledger_row(tracker, order_no):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute(
            "SELECT order_no, order_date, symbol, exchange, side, quantity, price, node_id "
            "FROM workflow_orders WHERE order_no = ?",
            (order_no,),
        ).fetchone()


def _ledger_count(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM workflow_orders").fetchone()[0]


def _response(order_no_field, value, *, error_msg=None, rsp_msg="정상처리"):
    resp = MagicMock()
    resp.error_msg = error_msg
    resp.rsp_msg = rsp_msg
    if value is None:
        resp.block2 = None
    else:
        block2 = MagicMock()
        setattr(block2, order_no_field, value)
        resp.block2 = block2
    return resp


def _ls_overseas_stock(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cosat00311 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls


def _ls_overseas_futures(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.CIDBT00900 = MagicMock(return_value=api)
    futs = MagicMock()
    futs.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_futureoption = MagicMock(return_value=futs)
    return ls


def _ls_korea_stock(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cspat00701 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=stock)
    return ls


# ---------------------------------------------------------------------------
# 해외주식
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overseas_stock_modify_inherits_original_side(tmp_path):
    """매도 주문을 정정해도 원장 행은 'sell' 이어야 한다(유령 롱 HWM 금지)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "sell", 7, 149.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890")),
        original_order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        new_quantity=10,
        new_price=150.0,
        side="buy",                    # 호출부 기본값 — 사실이 아니다
        config={"side": "buy"},
        context=ctx,
        node_id="modify-node",
    )

    assert result["modify_result"]["success"] is True
    row = _ledger_row(tracker, "67890")
    assert row is not None, "정정 새 주문번호가 원장에 기록되어야 한다"
    assert row[4] == "sell", "side 는 config 가 아니라 원 주문에서 승계해야 한다"
    assert (row[1], row[2], row[3]) == (TODAY, "AAPL", "NASDAQ")
    assert (row[5], row[6]) == (10, 150.0)
    assert row[7] == "modify-node"
    assert _ledger_count(tracker) == 2, "원 주문 행은 남긴다(잔여 체결이 늦게 올 수 있다)"


@pytest.mark.asyncio
async def test_overseas_stock_modify_does_not_touch_risk_tracker(tmp_path):
    """정정은 새 포지션이 아니다 — HWM 등록/해제 어느 쪽도 일으키지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=10, new_price=150.0, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert _ledger_row(tracker, "67890") is not None
    ctx._workflow_risk_tracker.register_symbol.assert_not_called()
    ctx._workflow_risk_tracker.unregister_symbol.assert_not_called()


@pytest.mark.asyncio
async def test_overseas_stock_quantity_only_modify_inherits_price(tmp_path):
    """수량만 정정하면 가격은 원 주문 값을 승계한다(0.0 으로 덮지 않는다)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=3, new_price=None, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (3, 149.0)


@pytest.mark.asyncio
async def test_overseas_stock_price_only_modify_inherits_quantity(tmp_path):
    """가격만 정정하면 수량은 원 주문 값을 승계한다(0 으로 덮지 않는다)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=None, new_price=151.5, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (7, 151.5)


@pytest.mark.asyncio
async def test_overseas_stock_modify_without_original_records_nothing(tmp_path):
    """원 주문을 원장에서 못 찾으면 기록하지 않는다(방향 추측 금지)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=10, new_price=150.0, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is True, "원장 기록 실패가 ACK 를 뒤집으면 안 된다"
    assert _ledger_count(tracker) == 0
    ctx._workflow_risk_tracker.register_symbol.assert_not_called()


@pytest.mark.asyncio
async def test_overseas_stock_empty_order_no_records_nothing(tmp_path):
    """빈 주문번호(거래시간 외 silent no-op)는 원장에 남기지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=10, new_price=150.0, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is False
    assert _ledger_count(tracker) == 1, "원 주문 행만 남아야 한다"


@pytest.mark.asyncio
async def test_overseas_stock_error_response_records_nothing(tmp_path):
    """브로커 에러 응답은 원장에 남기지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=_ls_overseas_stock(_response("OrdNo", "67890", error_msg="거래시간 외")),
        original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=10, new_price=150.0, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is False
    assert _ledger_count(tracker) == 1


# ---------------------------------------------------------------------------
# 해외선물
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overseas_futures_modify_inherits_original_side(tmp_path):
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", TODAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=_ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242")),
        original_order_id="98765",
        symbol="HMHM26",
        exchange="HKEX",
        new_quantity=2,
        new_price=20100.0,
        side="buy",                    # 호출부 기본값 — 사실이 아니다
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx,
        node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is True
    row = _ledger_row(tracker, "F-4242")
    assert row is not None
    assert row[4] == "sell"
    assert (row[2], row[3]) == ("HMHM26", "HKEX")
    assert (row[5], row[6]) == (2, 20100.0)
    ctx._workflow_risk_tracker.register_symbol.assert_not_called()


@pytest.mark.asyncio
async def test_overseas_futures_modify_without_original_is_refused(tmp_path):
    """원 주문을 못 찾으면 방향을 추측하지 않고 **요청 자체를 거른다**.

    CIDBT00900 은 BnsTpCode 를 필수로 받는다(blocks.py:88-93). 호출부가 넘기는
    side 는 존재하지 않는 config 키에서 온 값이라(노드 스키마에 side 없음)
    쓸 수 없다 — 그래서 브로커에 아무것도 보내지 않는다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls,
        original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="sell",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    assert "direction" in result["modify_result"]["error"]
    assert result["modified_order_id"] == ""
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()
    assert _ledger_count(tracker) == 0


@pytest.mark.asyncio
async def test_overseas_futures_empty_order_no_records_nothing(tmp_path):
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", TODAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=_ls_overseas_futures(_response("OvrsFutsOrdNo", "")),
        original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="sell",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    assert _ledger_count(tracker) == 1


# ---------------------------------------------------------------------------
# 국내주식
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_korea_stock_modify_inherits_original_side(tmp_path):
    """국내 경로는 config.get("side", "buy") 를 쓰고 있었다 — 그 값을 쓰면 안 된다."""
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "sell", 5, 70000.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=_ls_korea_stock(_response("OrdNo", "77777")),
        original_order_id="55555",
        symbol="005930",
        new_quantity=3,
        new_price=71000.0,
        config={},                     # side 키 자체가 없다 → 종전엔 "buy"
        context=ctx,
        node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is True
    row = _ledger_row(tracker, "77777")
    assert row is not None
    assert row[4] == "sell"
    assert (row[2], row[3]) == ("005930", "KRX")
    assert (row[5], row[6]) == (3, 71000.0)
    ctx._workflow_risk_tracker.register_symbol.assert_not_called()
    ctx._workflow_risk_tracker.unregister_symbol.assert_not_called()


@pytest.mark.asyncio
async def test_korea_stock_modify_without_original_records_nothing(tmp_path):
    ctx, tracker = _make_context(tmp_path, "korea_stock")

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=_ls_korea_stock(_response("OrdNo", "77777")),
        original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=71000.0, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is True
    assert _ledger_count(tracker) == 0


@pytest.mark.asyncio
async def test_korea_stock_empty_order_no_records_nothing(tmp_path):
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "buy", 5, 70000.0,
                         ctx.job_id, "order-node")

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=_ls_korea_stock(_response("OrdNo", "")),
        original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=71000.0, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is False
    assert _ledger_count(tracker) == 1


# ---------------------------------------------------------------------------
# 원 주문 조회 헬퍼 (context.find_workflow_order)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_workflow_order_matches_zero_padded_order_no(tmp_path):
    """ACK 의 '0000123' 과 정정 요청의 '123' 은 같은 주문이다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("0000123", TODAY, "AAPL", "NASDAQ", "sell", 7, 149.0,
                         ctx.job_id, "order-node")

    found = ctx.find_workflow_order("123", TODAY)
    assert found is not None and found["side"] == "sell"


@pytest.mark.asyncio
async def test_find_workflow_order_rejects_ambiguous_date_mismatch(tmp_path):
    """날짜가 다른 동일 주문번호가 둘 이상이면 모호하므로 None 이다.

    브로커 주문번호는 **날짜 안에서만** 유일하다 — 아무거나 집으면 어제 다른
    주문의 방향을 승계하게 된다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("777", "20260901", "AAPL", "NASDAQ", "buy", 1, 100.0,
                         ctx.job_id, "order-node")
    tracker.record_order("777", "20260902", "TSLA", "NASDAQ", "sell", 2, 200.0,
                         ctx.job_id, "order-node")

    assert ctx.find_workflow_order("777", TODAY) is None


@pytest.mark.asyncio
async def test_find_workflow_order_without_tracker_returns_none(tmp_path):
    ctx = ExecutionContext(job_id="no-tracker", workflow_id="offline")
    assert ctx.find_workflow_order("123", TODAY) is None


# ---------------------------------------------------------------------------
# 자정 관통 정정 — D±1 창 + 종목으로 가른다
#
# 종전에는 날짜가 어긋나면 **전 기간**을 훑어 후보가 정확히 1건일 때만
# 수용했다. 그런데 브로커 주문번호는 **영업일마다 리셋**되고(근거:
# database/workflow_position_tracker.py 모듈 독스트링 — 창 가드 수용조건 ④)
# 워크플로우 DB 는 며칠~몇 주 누적되므로, 과거 날짜에 같은 번호가 하나만 더
# 있으면 후보 2건 → None → side 미해결 → 브로커 호출 0회 거부가 됐다.
# 이제 트래커와 같은 D±1 창만 보고, 후보가 여러 건이면 종목으로 가른다.
# ---------------------------------------------------------------------------

YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")


@pytest.mark.asyncio
async def test_find_workflow_order_prefers_todays_row_over_an_older_same_number(tmp_path):
    """(1)(3) 오늘 행이 있으면 과거 동명 번호가 있어도 그대로 찾는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("42", "20260101", "TSLA", "NASDAQ", "sell", 9, 300.0,
                         ctx.job_id, "order-node")
    tracker.record_order("42", TODAY, "AAPL", "NASDAQ", "buy", 3, 150.0,
                         ctx.job_id, "order-node")

    found = ctx.find_workflow_order("42", TODAY, symbol="AAPL")
    assert found is not None
    assert (found["order_date"], found["symbol"], found["side"]) == (TODAY, "AAPL", "buy")


@pytest.mark.parametrize("recorded_date", ["yesterday", "tomorrow"])
@pytest.mark.asyncio
async def test_find_workflow_order_accepts_the_d_plus_minus_one_window(tmp_path, recorded_date):
    """(2) 어제/내일 행 + 같은 종목이면 찾는다(자정 관통)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    date = YESTERDAY if recorded_date == "yesterday" else TOMORROW
    tracker.record_order("42", date, "AAPL", "NASDAQ", "sell", 7, 149.0,
                         ctx.job_id, "order-node")

    found = ctx.find_workflow_order("42", TODAY, symbol="AAPL")
    assert found is not None
    assert (found["order_date"], found["side"]) == (date, "sell")


@pytest.mark.asyncio
async def test_find_workflow_order_window_ignores_rows_outside_d_plus_minus_one(tmp_path):
    """(3) 과거에 같은 주문번호가 있어도 창 후보를 정확히 고른다.

    종전 전 기간 폴백이었다면 후보 2건 → None 이다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("42", "20260101", "AAPL", "NASDAQ", "buy", 1, 10.0,
                         ctx.job_id, "order-node")
    tracker.record_order("42", YESTERDAY, "AAPL", "NASDAQ", "sell", 7, 149.0,
                         ctx.job_id, "order-node")

    found = ctx.find_workflow_order("42", TODAY, symbol="AAPL")
    assert found is not None
    assert (found["order_date"], found["side"]) == (YESTERDAY, "sell")


@pytest.mark.asyncio
async def test_find_workflow_order_window_rejects_a_symbol_mismatch(tmp_path):
    """(3) 창 후보의 종목이 다르면 남의 주문번호 재발급이다 — 쓰지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("42", YESTERDAY, "TSLA", "NASDAQ", "sell", 7, 300.0,
                         ctx.job_id, "order-node")

    assert ctx.find_workflow_order("42", TODAY, symbol="AAPL") is None


@pytest.mark.asyncio
async def test_find_workflow_order_rejects_two_window_rows_with_the_same_symbol(tmp_path):
    """(4) 종목까지 같은 창 후보가 둘 이상이면 모호하므로 None."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("42", YESTERDAY, "AAPL", "NASDAQ", "buy", 1, 100.0,
                         ctx.job_id, "order-node")
    tracker.record_order("42", TOMORROW, "AAPL", "NASDAQ", "sell", 2, 200.0,
                         ctx.job_id, "order-node")

    assert ctx.find_workflow_order("42", TODAY, symbol="AAPL") is None


@pytest.mark.asyncio
async def test_futures_modify_across_midnight_reaches_the_broker(tmp_path):
    """(2) 자정 관통 정정이 이제 브로커까지 간다 — 방향은 원장 승계."""
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", YESTERDAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",   # 호출부 기본값 — 사실이 아니다
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is True
    assert _futures_wire(ls).BnsTpCode == "1", "매도 주문 정정은 매도로 나가야 한다"
    assert _ledger_row(tracker, "F-4242")[4] == "sell"


@pytest.mark.asyncio
async def test_futures_modify_refuses_when_the_window_is_ambiguous(tmp_path):
    """(5) 방향을 못 찾으면 종전대로 브로커에 아무것도 보내지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", YESTERDAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")
    tracker.record_order("98765", TOMORROW, "HMHM26", "HKEX", "buy", 1, 20500.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()
    assert _ledger_count(tracker) == 2, "원 주문 두 행만 남아야 한다"


# ---------------------------------------------------------------------------
# 브로커 요청(와이어) — 원장과 갈리지 않는다
# ---------------------------------------------------------------------------

def _stock_wire(ls):
    """cosat00311 에 실제로 넘어간 COSAT00311InBlock1."""
    return ls.overseas_stock().주문().cosat00311.call_args.args[0]


def _futures_wire(ls):
    """CIDBT00900 에 실제로 넘어간 CIDBT00900InBlock1."""
    return ls.overseas_futureoption().order().CIDBT00900.call_args.args[0]


def _korea_wire(ls):
    """cspat00701 에 실제로 넘어간 CSPAT00701InBlock1."""
    return ls.korea_stock().order().cspat00701.call_args.kwargs["body"]


@pytest.mark.asyncio
async def test_overseas_stock_quantity_only_modify_sends_original_price_on_the_wire(tmp_path):
    """수량만 정정하면 **브로커에도** 원 가격이 나간다(0.0 아님).

    COSAT00311 의 OvrsOrdPrc 는 "Revised order price"(blocks.py:85-92)이고
    SDK 예제도 실제 값을 싣는다(example/overseas_stock/run_COSAT00311.py:36-37).
    어디에도 '0 = 변경 없음' 규약이 없다. 종전 `new_price or 0.0` 은 브로커에
    가격 0 을 보내면서 원장에는 149.0 을 적는 **불일치**였다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=3, new_price=None, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    wire = _stock_wire(ls)
    assert (wire.OrdQty, wire.OvrsOrdPrc) == (3, 149.0)
    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OvrsOrdPrc), "원장과 와이어가 같아야 한다"


@pytest.mark.asyncio
async def test_overseas_stock_price_only_modify_sends_original_quantity_on_the_wire(tmp_path):
    """가격만 정정하면 브로커에도 원 수량이 나간다(0 아님)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=None, new_price=151.5, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    wire = _stock_wire(ls)
    assert (wire.OrdQty, wire.OvrsOrdPrc) == (7, 151.5)
    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OvrsOrdPrc)


@pytest.mark.asyncio
async def test_overseas_stock_modify_without_original_and_partial_fields_is_refused(tmp_path):
    """승계할 원 주문도 없고 안 바꾼 필드도 있으면 **보내지 않는다**.

    0 은 어느 정정 TR 에서도 '변경 없음' 이 아니다 — 보내면 가격 0 짜리
    지정가 정정이 된다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=3, new_price=None, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is False
    ls.overseas_stock().주문().cosat00311.assert_not_called()
    assert _ledger_count(tracker) == 0


@pytest.mark.asyncio
async def test_overseas_futures_wire_uses_ledger_side_not_config(tmp_path):
    """BnsTpCode 는 원 주문 원장 행의 방향이다 — config 의 "buy" 가 아니다.

    CIDBT00900 blocks.py:88-93 — "'1' = sell (매도), '2' = buy (매수)".
    매도 선물 주문을 정정하는데 종전 코드는 언제나 '2'(매수)를 보냈다
    (호출부의 `config.get("side", "buy")` 가 노드 스키마에 없는 키라서).
    ⚠️ LS 가 불일치 BnsTpCode 를 어떻게 처리하는지는 미관측이다.
    """
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", TODAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=None, new_price=20100.0,
        side="buy",                    # 호출부 기본값 — 사실이 아니다
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    wire = _futures_wire(ls)
    assert wire.BnsTpCode == "1", "매도 주문 정정은 매도로 나가야 한다"
    assert (wire.OrdQty, wire.OvrsDrvtOrdPrc) == (1, 20100.0), "안 바꾼 수량은 승계"
    row = _ledger_row(tracker, "F-4242")
    assert (row[4], row[5], row[6]) == ("sell", wire.OrdQty, wire.OvrsDrvtOrdPrc)


@pytest.mark.asyncio
async def test_overseas_futures_buy_order_still_sends_buy(tmp_path):
    """반대 방향도 승계한다(가드가 '항상 매도' 로 뒤집히지 않았다)."""
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", TODAY, "HMHM26", "HKEX", "buy", 1, 20000.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="sell", config={},
        context=ctx, node_id="modify-fut",
    )

    assert _futures_wire(ls).BnsTpCode == "2"


@pytest.mark.asyncio
async def test_korea_stock_quantity_only_modify_sends_original_price_on_the_wire(tmp_path):
    """국내도 마찬가지 — 특히 OrdPrc 0 은 '변경 없음' 이 아니라 **시장가용 값**이다.

    CSPAT00701 blocks.py:100-107 — "Use 0 for market orders ('03') and other
    non-limit price types". 지정가('00')로 0 을 보내면 가격 0 이다.
    """
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "sell", 5, 70000.0,
                         ctx.job_id, "order-node")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=None, config={},
        context=ctx, node_id="modify-kr",
    )

    wire = _korea_wire(ls)
    assert (wire.OrdQty, wire.OrdPrc) == (3, 70000.0)
    assert wire.OrdprcPtnCode == "00", "지정가로 보내면서 가격 0 을 실으면 안 된다"
    row = _ledger_row(tracker, "77777")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OrdPrc)


@pytest.mark.asyncio
async def test_korea_stock_modify_without_original_and_partial_fields_is_refused(tmp_path):
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=None, new_price=71000.0, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is False
    ls.korea_stock().order().cspat00701.assert_not_called()
    assert _ledger_count(tracker) == 0


@pytest.mark.asyncio
async def test_find_workflow_order_returns_none_for_a_tracker_without_scope(tmp_path):
    """독스트링의 계약 — 조회 실패는 **None** 이지 예외가 아니다.

    scope 계산(`tracker.product/provider/trading_mode`)과 `tracker.db_path` 독출이
    try 바깥에 있으면, 그 속성이 없는 트래커를 물었을 때 AttributeError 가
    호출자(정정 경로)로 올라가 정정 자체를 죽인다.
    """
    ctx = ExecutionContext(job_id="bad-tracker", workflow_id="offline")

    class TrackerWithoutScope:
        pass

    ctx._workflow_position_tracker = TrackerWithoutScope()
    assert ctx.find_workflow_order("123", TODAY) is None


# ---------------------------------------------------------------------------
# Y1 — '원장에 행이 없다' 와 '원장 자체가 없다' 는 다른 실패다
#
# 트래커는 워크플로우에 PnL 리스너가 하나라도 있을 때만 만들어진다
# (context.init_workflow_position_tracker 의
#  `any(hasattr(l, 'on_workflow_pnl_update') ...)` 게이트, 또는 init 예외 시 None).
# 리스너 0개로 엔진을 라이브러리처럼 직접 구동하면 record_workflow_order 가 no-op 이라
# 원장에 행이 생길 수 없고 find_workflow_order 는 영원히 None 이다 — 방향을 원장에서만
# 찾으면 해외선물 정정이 그 구성에서 **전면 불능**이 된다(매수든 매도든).
# 그래서 (1) 사유를 갈라 말하고, (2) 호출자가 side 를 실제로 준 경우엔 그 값을 쓴다.
# 추측('항상 buy')으로 되돌리지는 않는다 — 매도 주문에 매수 구분을 보내는 건 실계좌
# 위험이고(불일치 BnsTpCode 처리는 **미관측**), 실패를 명확히 알리는 편이 낫다.
# ---------------------------------------------------------------------------

def _context_without_ledger():
    """PnL 리스너 0개 구성 — 트래커가 아예 없다."""
    ctx = ExecutionContext(job_id="no-ledger", workflow_id="offline")
    ctx._workflow_risk_tracker = MagicMock()
    assert ctx.has_workflow_order_ledger() is False
    return ctx


@pytest.mark.asyncio
async def test_futures_modify_without_a_ledger_reports_ledger_unavailable(tmp_path):
    """(a) 트래커 None + side 미제공 → ledger_unavailable 사유, 브로커 호출 0회."""
    ctx = _context_without_ledger()
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",   # 호출부 기본값 — 사실이 아니다
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    error = result["modify_result"]["error"]
    assert error.startswith("ledger_unavailable:"), error
    assert "original_order_not_found" not in error, "원장 미조회와 원장 부재를 갈라야 한다"
    assert "no workflow order ledger" in error
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()


@pytest.mark.asyncio
async def test_futures_modify_with_a_ledger_but_no_row_reports_order_not_found(tmp_path):
    """대조군 — 원장은 있는데 그 주문 행이 없으면 사유가 다르다."""
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    assert result["modify_result"]["error"].startswith("original_order_not_found:")
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()


@pytest.mark.asyncio
async def test_futures_modify_without_a_ledger_uses_an_explicit_config_side(tmp_path):
    """(b) 트래커 None + side='sell' 명시 → BnsTpCode='1' 로 브로커에 도달한다.

    이건 추측이 아니라 **호출자가 알려준 값**이다(노드 스키마엔 side 가 없지만
    라이브러리 직접 호출자는 config 에 넣을 수 있다).
    """
    ctx = _context_without_ledger()
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",
        config={"expiry_month": "202606", "exchange_code": "HKEX", "side": "sell"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is True
    wire = _futures_wire(ls)
    assert wire.BnsTpCode == "1", "호출자가 sell 이라고 했으면 매도로 나가야 한다"
    assert (wire.OrdQty, wire.OvrsDrvtOrdPrc) == (2, 20100.0)


@pytest.mark.asyncio
async def test_futures_modify_without_a_ledger_logs_the_caller_supplied_side(tmp_path, caplog):
    """명시 side 를 쓴 사실은 로그에 남는다(운영자가 근거를 볼 수 있어야 한다)."""
    ctx = _context_without_ledger()
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    with caplog.at_level(logging.WARNING, logger="programgarden.executor"):
        await ModifyOrderNodeExecutor()._modify_overseas_futures(
            ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
            new_quantity=2, new_price=20100.0, side="buy",
            config={"exchange_code": "HKEX", "side": "sell"},
            context=ctx, node_id="modify-fut",
        )

    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("caller-supplied side" in m and "'sell'" in m for m in messages), messages


@pytest.mark.asyncio
async def test_futures_modify_still_refuses_an_unusable_explicit_side(tmp_path):
    """side 값이 buy/sell 이 아니면 '안 준 것' 과 같다 — 거부한다."""
    ctx = _context_without_ledger()
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",
        config={"exchange_code": "HKEX", "side": "long"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    assert result["modify_result"]["error"].startswith("ledger_unavailable:")
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()


@pytest.mark.asyncio
async def test_futures_modify_without_a_ledger_still_needs_the_unchanged_fields(tmp_path):
    """명시 side 가 있어도 승계할 수량/가격이 없으면 보내지 않는다(0 은 '변경 없음' 이 아니다)."""
    ctx = _context_without_ledger()
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=None, new_price=20100.0, side="buy",
        config={"exchange_code": "HKEX", "side": "sell"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is False
    assert result["modify_result"]["error"].startswith("unchanged_field_unresolved:")
    assert "no order ledger at all" in result["modify_result"]["error"]
    ls.overseas_futureoption().order().CIDBT00900.assert_not_called()


@pytest.mark.asyncio
async def test_futures_modify_with_a_ledger_row_ignores_a_conflicting_config_side(tmp_path):
    """(c) 트래커 있음 + 원장에 행 있음 → 4차 동작 그대로(원장이 이긴다)."""
    ctx, tracker = _make_context(tmp_path, "overseas_futures")
    tracker.record_order("98765", TODAY, "HMHM26", "HKEX", "sell", 1, 20000.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_futures(_response("OvrsFutsOrdNo", "F-4242"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_futures(
        ls=ls, original_order_id="98765", symbol="HMHM26", exchange="HKEX",
        new_quantity=2, new_price=20100.0, side="buy",
        # 호출자가 buy 라고 우겨도 원장 행(sell)이 이긴다 — 원장은 우리가 실제로
        # 브로커에 보낸 값의 기록이다.
        config={"exchange_code": "HKEX", "side": "buy"},
        context=ctx, node_id="modify-fut",
    )

    assert result["modify_result"]["success"] is True
    assert _futures_wire(ls).BnsTpCode == "1"
    assert _ledger_row(tracker, "F-4242")[4] == "sell"


@pytest.mark.asyncio
async def test_overseas_stock_modify_without_a_ledger_records_the_explicit_side(tmp_path):
    """방향이 필요 없는 경로(COSAT00311)도 명시 side 가 있으면 그걸 쓴다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=10, new_price=150.0, side="buy",
        config={"side": "sell"},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is True
    row = _ledger_row(tracker, "67890")
    assert row is not None and row[4] == "sell"


# ---------------------------------------------------------------------------
# Y3 — 소수 수량은 자르지 않고 **거부**한다
#
# 세 정정 TR 의 수량 필드는 모두 정수다(COSAT00311 blocks.py:79 / CIDBT00900
# blocks.py:130 / CSPAT00701 blocks.py:74 — 전부 `OrdQty: int`). 그런데 LS 해외주식은
# 소수점 거래가 실재한다(prod 2026-08-24 IBM 0.847972주 실측). `int(quantity)` 로
# 싣던 종전 코드는 브로커엔 OrdQty=0 을 보내고 원장엔 0.847972 를 남겨, 이 구조가
# 지키려던 '와이어=원장' 불변식을 스스로 깼다.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modify_refuses_a_fractional_inherited_quantity(tmp_path):
    """가격만 정정 + 원 주문이 소수 수량 → 보내지 않는다(OrdQty=0 방지)."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "IBM", "NYSE", "buy", 0.847972, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="IBM", exchange="NYSE",
        new_quantity=None, new_price=151.5, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is False
    error = result["modify_result"]["error"]
    assert error.startswith("non_integer_quantity:"), error
    assert "0.847972" in error
    ls.overseas_stock().주문().cosat00311.assert_not_called()
    assert _ledger_count(tracker) == 1, "원 주문 행만 남는다"


@pytest.mark.asyncio
async def test_modify_refuses_a_fractional_new_quantity(tmp_path):
    """호출자가 소수 수량을 직접 줘도 마찬가지다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "IBM", "NYSE", "buy", 3, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="IBM", exchange="NYSE",
        new_quantity=0.5, new_price=151.5, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is False
    assert result["modify_result"]["error"].startswith("non_integer_quantity:")
    ls.overseas_stock().주문().cosat00311.assert_not_called()


@pytest.mark.asyncio
async def test_modify_refuses_a_zero_quantity(tmp_path):
    """정수 0 도 막는다 — 절단 버그와 결과(OrdQty=0)가 같다."""
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "buy", 5, 70000.0,
                         ctx.job_id, "order-node")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=0, new_price=71000.0, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is False
    assert result["modify_result"]["error"].startswith("non_positive_quantity:")
    ls.korea_stock().order().cspat00701.assert_not_called()


@pytest.mark.asyncio
async def test_modify_accepts_an_integral_float_quantity(tmp_path):
    """정수값 float(7.0)은 정상 — 와이어에는 int 7 이 실린다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "AAPL", "NASDAQ", "buy", 7.0, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="AAPL", exchange="NASDAQ",
        new_quantity=None, new_price=151.5, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    wire = _stock_wire(ls)
    assert wire.OrdQty == 7 and isinstance(wire.OrdQty, int)
    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OvrsOrdPrc), "원장과 와이어가 같아야 한다"


# ---------------------------------------------------------------------------
# 승계 가격 게이트 — 시장가로 낸 주문의 원장 price 0.0 을 정정에 다시 싣지 않는다
#
# 원장 price 는 '브로커에 실제로 보낸 값' 이다. 국내주식 시장가 신규주문은
# `ord_prc = 0.0 if ordprc_ptn_code == "03"` 을 그대로 기록하고(해외주식 매도
# 시장가도 `price = 0.0`), 체결 전(= 정정 가능한 상태)에는
# update_workflow_order_fill_price 가 아직 실체결가를 채우지 않았다. 그 0.0 을
# 수량만 정정할 때 승계해 지정가('00')로 보내면 '변경 없음' 이 아니라 **가격 0
# 주문**이다(CSPAT00701 blocks.py:100-107 — 0 은 시장가용 값). non_positive_quantity
# 게이트와 같은 모양의 구멍이 가격 축에 있었다.
#
# 게이트는 **승계값에만** 건다 — 호출자가 new_price=0 을 명시하면 막지 않는다
# (그 조합의 유효성은 우리가 판정하지 않는다).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ledger_price",
    [
        0.0,   # 시장가 신규주문이 원장에 남기는 값(실제 관측되는 형태)
        -1.0,  # 게이트 조건(<= 0)의 경계 확인용 — 원장에서 관측된 값은 아니다
    ],
)
async def test_modify_refuses_to_inherit_a_non_positive_price(tmp_path, ledger_price):
    """(a) 원장 price 0.0(시장가) + new_quantity 만 → 거부 + 브로커 호출 0회."""
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "buy", 5, ledger_price,
                         ctx.job_id, "order-node")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=None, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is False
    error = result["modify_result"]["error"]
    assert error.startswith("non_positive_inherited_price:"), error
    assert "시장가로 낸 주문은 가격을 승계할 수 없다" in error
    assert "new_price 를 명시하라" in error
    ls.korea_stock().order().cspat00701.assert_not_called()
    assert _ledger_count(tracker) == 1, "원 주문 행만 남는다(정정 행 없음)"


@pytest.mark.asyncio
async def test_modify_of_a_market_order_passes_with_an_explicit_price(tmp_path):
    """(b) 같은 상황 + new_price 명시 → 통과. 와이어와 원장이 그 값을 같이 싣는다."""
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "buy", 5, 0.0,
                         ctx.job_id, "order-node")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=71000.0, config={},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is True, result
    wire = _korea_wire(ls)
    assert (wire.OrdQty, wire.OrdPrc, wire.OrdprcPtnCode) == (3, 71000.0, "00")
    row = _ledger_row(tracker, "77777")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OrdPrc), "원장과 와이어가 같아야 한다"


@pytest.mark.asyncio
async def test_modify_does_not_block_an_explicitly_stated_zero_price(tmp_path):
    """(c) new_price=0 **명시** → 게이트가 막지 않고 브로커까지 도달한다.

    그건 호출자의 진술이다. CSPAT00701 에서는 시장가 유형('03')과 함께 유효할 수
    있다(blocks.py:100-107 "Use 0 for market orders ('03')"). 그 조합의 유효성은
    엔진이 판정하지 않는다 — 호출자가 준 값을 그대로 싣는다.
    """
    ctx, tracker = _make_context(tmp_path, "korea_stock")
    tracker.record_order("55555", TODAY, "005930", "KRX", "buy", 5, 70000.0,
                         ctx.job_id, "order-node")
    ls = _ls_korea_stock(_response("OrdNo", "77777"))

    result = await ModifyOrderNodeExecutor()._modify_korea_stock(
        ls=ls, original_order_id="55555", symbol="005930",
        new_quantity=3, new_price=0, config={"price_type_code": "03"},
        context=ctx, node_id="modify-kr",
    )

    assert result["modify_result"]["success"] is True, result
    ls.korea_stock().order().cspat00701.assert_called_once()
    wire = _korea_wire(ls)
    assert (wire.OrdQty, wire.OrdPrc, wire.OrdprcPtnCode) == (3, 0.0, "03")
    row = _ledger_row(tracker, "77777")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OrdPrc), "원장과 와이어가 같아야 한다"


@pytest.mark.asyncio
async def test_modify_inherits_a_positive_ledger_price(tmp_path):
    """(d) 원장 price 149.0 승계 → 통과. 게이트는 양수 승계값을 건드리지 않는다."""
    ctx, tracker = _make_context(tmp_path, "overseas_stock")
    tracker.record_order("12345", TODAY, "IBM", "NYSE", "buy", 5, 149.0,
                         ctx.job_id, "order-node")
    ls = _ls_overseas_stock(_response("OrdNo", "67890"))

    result = await ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls, original_order_id="12345", symbol="IBM", exchange="NYSE",
        new_quantity=3, new_price=None, side="buy", config={},
        context=ctx, node_id="modify-node",
    )

    assert result["modify_result"]["success"] is True, result
    ls.overseas_stock().주문().cosat00311.assert_called_once()
    wire = _stock_wire(ls)
    assert (wire.OrdQty, wire.OvrsOrdPrc) == (3, 149.0)
    row = _ledger_row(tracker, "67890")
    assert (row[5], row[6]) == (wire.OrdQty, wire.OvrsOrdPrc), "원장과 와이어가 같아야 한다"

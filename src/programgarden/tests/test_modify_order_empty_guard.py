"""정정주문 빈-주문번호 가드 회귀 테스트.

LS 정정주문 TR 이 휴장(거래시간 외) 등에서 `error_msg` 없이 빈 주문번호를
반환하는 silent no-op 을 executor 가 `modify_result.success=False` 로 차단하는지
검증한다. 라이브 키 없이 mock LS response 만으로 3개 modify 경로를 검증한다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.executor import CancelOrderNodeExecutor, ModifyOrderNodeExecutor


def _make_context():
    ctx = MagicMock()
    ctx.log = MagicMock()
    return ctx


def _make_ls_overseas_stock(response):
    """ls.overseas_stock().주문().cosat00311(...).req_async() -> response 체인."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cosat00311 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls


def _make_ls_overseas_futures(response):
    """ls.overseas_futureoption().order().CIDBT00900(...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.CIDBT00900 = MagicMock(return_value=api)
    futs = MagicMock()
    futs.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_futureoption = MagicMock(return_value=futs)
    return ls


def _make_ls_korea_stock(response):
    """ls.korea_stock().order().cspat00701(body=...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cspat00701 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=stock)
    return ls


# --------------------------------------------------------------------------
# 빈-주문번호 가드 (silent no-op 차단)
# --------------------------------------------------------------------------

def test_modify_overseas_stock_empty_order_no_blocked():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"
    block2 = MagicMock()
    block2.OrdNo = ""  # 거래시간 외 silent no-op
    resp.block2 = block2

    ls = _make_ls_overseas_stock(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_overseas_stock(
        ls=ls,
        original_order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        new_quantity=10,
        new_price=150.0,
        side="buy",
        config={},
        context=ctx,
        node_id="modify-1",
    ))

    assert result["modify_result"]["success"] is False
    assert "Empty modify order number" in result["modify_result"]["error"]
    assert result["modified_order"] is None
    assert result["modify_result"]["product"] == "overseas_stock"
    # top-level 포트 키 (modified_order_id) 가 빈 문자열로 emit 되어야 함
    assert result["modified_order_id"] == ""


def test_modify_overseas_futures_empty_order_no_blocked():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = None  # rsp_msg 도 없는 최악 케이스 -> "정정 미반영" fallback
    block2 = MagicMock()
    block2.OvrsFutsOrdNo = ""
    resp.block2 = block2

    ls = _make_ls_overseas_futures(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_overseas_futures(
        ls=ls,
        original_order_id="98765",
        symbol="HMHM26",
        exchange="HKEX",
        new_quantity=1,
        new_price=20000.0,
        side="sell",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx,
        node_id="modify-2",
    ))

    assert result["modify_result"]["success"] is False
    assert "Empty modify order number" in result["modify_result"]["error"]
    assert "정정 미반영" in result["modify_result"]["error"]
    assert result["modified_order"] is None
    assert result["modify_result"]["product"] == "overseas_futures"
    assert result["modified_order_id"] == ""


def test_modify_korea_stock_empty_order_no_blocked():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "장 종료"
    block2 = MagicMock()
    block2.OrdNo = ""
    resp.block2 = block2

    ls = _make_ls_korea_stock(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_korea_stock(
        ls=ls,
        original_order_id="55555",
        symbol="005930",
        new_quantity=5,
        new_price=70000.0,
        config={},
        context=ctx,
        node_id="modify-3",
    ))

    assert result["modify_result"]["success"] is False
    assert "Empty modify order number" in result["modify_result"]["error"]
    assert result["modified_order"] is None
    assert result["modify_result"]["product"] == "korea_stock"
    assert result["modified_order_id"] == ""


def test_modify_block2_none_blocked():
    """block2 자체가 None 이어도 가드가 동작한다 (overseas_stock 기준)."""
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "거래시간 아님"
    resp.block2 = None

    ls = _make_ls_overseas_stock(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_overseas_stock(
        ls=ls,
        original_order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        new_quantity=10,
        new_price=150.0,
        side="buy",
        config={},
        context=ctx,
        node_id="modify-4",
    ))

    assert result["modify_result"]["success"] is False
    assert "Empty modify order number" in result["modify_result"]["error"]
    assert result["modified_order"] is None
    assert result["modified_order_id"] == ""


# --------------------------------------------------------------------------
# 정상 케이스 회귀 (new_order_no 있음 -> success=True)
# --------------------------------------------------------------------------

def test_modify_overseas_stock_success_regression():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"
    block2 = MagicMock()
    block2.OrdNo = "67890"
    resp.block2 = block2

    ls = _make_ls_overseas_stock(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_overseas_stock(
        ls=ls,
        original_order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        new_quantity=10,
        new_price=150.0,
        side="buy",
        config={},
        context=ctx,
        node_id="modify-ok",
    ))

    assert result["modify_result"]["success"] is True
    assert result["modify_result"]["new_order_id"] == "67890"
    assert result["modified_order"] is not None
    assert result["modified_order"]["status"] == "modified"
    # top-level 포트 키가 new_order_no 로 배선되어야 함
    assert result["modified_order_id"] == "67890"


def test_modify_overseas_futures_success_regression():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"
    block2 = MagicMock()
    block2.OvrsFutsOrdNo = "F-4242"
    resp.block2 = block2

    ls = _make_ls_overseas_futures(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_overseas_futures(
        ls=ls,
        original_order_id="98765",
        symbol="HMHM26",
        exchange="HKEX",
        new_quantity=1,
        new_price=20000.0,
        side="sell",
        config={"expiry_month": "202606", "exchange_code": "HKEX"},
        context=ctx,
        node_id="modify-fut-ok",
    ))

    assert result["modify_result"]["success"] is True
    assert result["modify_result"]["new_order_id"] == "F-4242"
    assert result["modified_order"] is not None
    assert result["modified_order"]["status"] == "modified"
    assert result["modified_order_id"] == "F-4242"


def test_modify_korea_stock_success_regression():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"
    block2 = MagicMock()
    block2.OrdNo = "K-777"
    resp.block2 = block2

    ls = _make_ls_korea_stock(resp)
    ctx = _make_context()
    executor = ModifyOrderNodeExecutor()

    result = asyncio.run(executor._modify_korea_stock(
        ls=ls,
        original_order_id="55555",
        symbol="005930",
        new_quantity=5,
        new_price=70000.0,
        config={},
        context=ctx,
        node_id="modify-kr-ok",
    ))

    assert result["modify_result"]["success"] is True
    assert result["modify_result"]["new_order_id"] == "K-777"
    assert result["modified_order"] is not None
    assert result["modified_order"]["status"] == "modified"
    assert result["modified_order_id"] == "K-777"


# --------------------------------------------------------------------------
# 취소 성공 시 top-level cancelled_order_id 배선 회귀
# --------------------------------------------------------------------------

def _make_ls_cancel_overseas_stock(response):
    """ls.overseas_stock().주문().cosat00301(...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cosat00301 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls


def _make_ls_cancel_overseas_futures(response):
    """ls.overseas_futureoption().order().CIDBT01000(...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.CIDBT01000 = MagicMock(return_value=api)
    futs = MagicMock()
    futs.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_futureoption = MagicMock(return_value=futs)
    return ls


def _make_ls_cancel_korea_stock(response):
    """ls.korea_stock().order().cspat00801(body=...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cspat00801 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=stock)
    return ls


def test_cancel_overseas_stock_success_sets_port():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"

    ls = _make_ls_cancel_overseas_stock(resp)
    ctx = _make_context()
    executor = CancelOrderNodeExecutor()

    result = asyncio.run(executor._cancel_overseas_stock(
        ls=ls,
        order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        config={},
        context=ctx,
        node_id="cancel-1",
    ))

    assert result["cancel_result"]["success"] is True
    assert result["cancelled_order"] is not None
    assert result["cancelled_order_id"] == "12345"


def test_cancel_overseas_futures_success_sets_port():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"

    ls = _make_ls_cancel_overseas_futures(resp)
    ctx = _make_context()
    executor = CancelOrderNodeExecutor()

    result = asyncio.run(executor._cancel_overseas_futures(
        ls=ls,
        order_id="98765",
        symbol="HMHM26",
        exchange="HKEX",
        config={},
        context=ctx,
        node_id="cancel-2",
    ))

    assert result["cancel_result"]["success"] is True
    assert result["cancelled_order"] is not None
    assert result["cancelled_order_id"] == "98765"


def test_cancel_korea_stock_success_sets_port():
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"

    ls = _make_ls_cancel_korea_stock(resp)
    ctx = _make_context()
    executor = CancelOrderNodeExecutor()

    result = asyncio.run(executor._cancel_korea_stock(
        ls=ls,
        order_id="55555",
        symbol="005930",
        config={"quantity": 5},
        context=ctx,
        node_id="cancel-3",
    ))

    assert result["cancel_result"]["success"] is True
    assert result["cancelled_order"] is not None
    assert result["cancelled_order_id"] == "55555"


def test_cancel_overseas_stock_error_sets_empty_port():
    resp = MagicMock()
    resp.error_msg = "거래시간 외"
    resp.rsp_msg = "거래시간 외"

    ls = _make_ls_cancel_overseas_stock(resp)
    ctx = _make_context()
    executor = CancelOrderNodeExecutor()

    result = asyncio.run(executor._cancel_overseas_stock(
        ls=ls,
        order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        config={},
        context=ctx,
        node_id="cancel-err",
    ))

    assert result["cancel_result"]["success"] is False
    assert result["cancelled_order"] is None
    assert result["cancelled_order_id"] == ""

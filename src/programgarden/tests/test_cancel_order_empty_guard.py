"""취소주문 빈-주문번호 가드 + 해외주식 시장코드 회귀 테스트.

두 결함을 고정한다 (2026-08-19).

1. **취소가 살아 있는 주문을 "취소됨" 으로 보고하던 문제.**
   취소 3경로(해외주식/해외선물/국내주식)가 `response.error_msg` 부재만 보고
   성공 처리했다. LS 는 업무 거부(이미 체결됨·원주문 없음·휴장 등)를 error_msg
   없이 HTTP 200 + 오류 rsp_cd 로 돌려주고, 그때 취소주문번호가 0/빈 값으로 온다.
   정정(modify)에는 이미 같은 가드가 있었는데 취소에만 없어 **비대칭**이었다 —
   취소는 "이미 체결됨" 류 거부가 정상 빈발 경로라 정정보다 더 아프다.

2. **AMEX 주문/정정/취소가 요청 생성 단계에서 죽던 문제.**
   엔진이 AMEX 를 `"83"` 으로 보냈는데 LS SDK 의 `OrdMktCode` 는
   `Literal["81","82"]` 라 pydantic ValidationError 로 죽었다(시세 g3101 의
   exchcd 도 마찬가지고 SDK 어디에도 "83" 은 없다). 엔진의 실시간·관심종목
   경로는 이미 AMEX→"81" 로 매핑하고 있어 내부적으로도 어긋나 있었다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden.executor import (
    OVERSEAS_STOCK_MARKET_CODES,
    CancelOrderNodeExecutor,
    ModifyOrderNodeExecutor,
    NewOrderNodeExecutor,
)


def _make_context():
    ctx = MagicMock()
    ctx.log = MagicMock()
    return ctx


def _make_ls_overseas_stock(response):
    """ls.overseas_stock().주문().cosat00301(...).req_async() -> response."""
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cosat00301 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls, order


def _make_ls_overseas_futures(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.CIDBT01000 = MagicMock(return_value=api)
    futs = MagicMock()
    futs.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_futureoption = MagicMock(return_value=futs)
    return ls, order


def _make_ls_korea_stock(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cspat00801 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.order = MagicMock(return_value=order)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=stock)
    return ls, order


def _rejected(order_no_attr: str, value, rsp_cd="40510", rsp_msg="이미 체결된 주문입니다"):
    """error_msg 없이 오는 업무 거부 응답 — 가장 위험한 형태."""
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_cd = rsp_cd
    resp.rsp_msg = rsp_msg
    block2 = MagicMock()
    setattr(block2, order_no_attr, value)
    resp.block2 = block2
    return resp


def _accepted(order_no_attr: str, value):
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_cd = "00000"
    resp.rsp_msg = "정상처리 되었습니다."
    block2 = MagicMock()
    setattr(block2, order_no_attr, value)
    resp.block2 = block2
    return resp


# ---------------------------------------------------------------------------
# 1. 빈 취소주문번호 → 실패로 차단 (살아 있는 주문 오보 방지)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", ["", 0, "0", None])
def test_cancel_overseas_stock_empty_order_no_blocked(empty):
    ls, _ = _make_ls_overseas_stock(_rejected("OrdNo", empty))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_overseas_stock(
        ls=ls, order_id="12345", symbol="AAPL", exchange="NASDAQ",
        config={}, context=_make_context(), node_id="cancel-1",
    ))

    assert result["cancel_result"]["success"] is False
    assert "접수되지 않았습니다" in result["cancel_result"]["error"]
    # 거부 사유를 버리면 사용자는 왜 안 됐는지 알 수 없다.
    assert result["cancel_result"]["rsp_cd"] == "40510"
    assert "이미 체결" in result["cancel_result"]["rsp_msg"]
    # 🔴 취소 안 된 주문을 취소된 것으로 흘려보내면 안 된다.
    assert result["cancelled_order_id"] == ""
    assert result["cancelled_order"] is None


def test_cancel_overseas_futures_empty_order_no_blocked():
    """선물 응답의 주문번호는 OrdNo 가 아니라 OvrsFutsOrdNo 다."""
    ls, _ = _make_ls_overseas_futures(_rejected("OvrsFutsOrdNo", ""))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_overseas_futures(
        ls=ls, order_id="98765", symbol="HMHM26", exchange="HKEX",
        config={}, context=_make_context(), node_id="cancel-2",
    ))

    assert result["cancel_result"]["success"] is False
    assert result["cancelled_order_id"] == ""
    assert result["cancelled_order"] is None


def test_cancel_korea_stock_empty_order_no_blocked():
    """국내는 실전 계좌 전용(모의투자 없음)이라 오보의 대가가 가장 크다."""
    ls, _ = _make_ls_korea_stock(_rejected("OrdNo", 0))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_korea_stock(
        ls=ls, order_id="55555", symbol="005930",
        config={"quantity": 1}, context=_make_context(), node_id="cancel-3",
    ))

    assert result["cancel_result"]["success"] is False
    assert result["cancelled_order_id"] == ""
    assert result["cancelled_order"] is None


# ---------------------------------------------------------------------------
# 정상 취소는 그대로 통과해야 한다 (가드가 과하면 멀쩡한 취소가 막힌다)
# ---------------------------------------------------------------------------


def test_cancel_overseas_stock_accepted_passes_and_keeps_both_ids():
    ls, _ = _make_ls_overseas_stock(_accepted("OrdNo", 778899))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_overseas_stock(
        ls=ls, order_id="12345", symbol="AAPL", exchange="NASDAQ",
        config={}, context=_make_context(), node_id="cancel-ok",
    ))

    assert result["cancel_result"]["success"] is True
    # 취소는 그 자체로 새 주문번호를 받는다 — 원주문번호와 뒤섞이면 후속 조회가
    # 엉뚱한 주문을 건드린다.
    assert result["cancel_result"]["order_id"] == "12345"
    assert result["cancel_result"]["cancel_order_no"] == "778899"
    assert result["cancelled_order_id"] == "12345"


def test_cancel_korea_stock_accepted_passes():
    ls, _ = _make_ls_korea_stock(_accepted("OrdNo", 555))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_korea_stock(
        ls=ls, order_id="55555", symbol="005930",
        config={"quantity": 1}, context=_make_context(), node_id="cancel-ok-kr",
    ))

    assert result["cancel_result"]["success"] is True
    assert result["cancel_result"]["cancel_order_no"] == "555"


# ---------------------------------------------------------------------------
# 2. 해외주식 시장코드 — LS 는 "81"/"82" 만 받는다
# ---------------------------------------------------------------------------


def test_market_codes_never_emit_unsupported_83():
    """SDK 의 OrdMktCode/exchcd 는 Literal["81","82"] — "83" 은 요청을 죽인다."""
    assert set(OVERSEAS_STOCK_MARKET_CODES.values()) <= {"81", "82"}


def test_amex_maps_to_nyse_code():
    """AMEX(현 NYSE American)는 전용 코드가 없어 NYSE 와 같은 81 로 보낸다."""
    assert OVERSEAS_STOCK_MARKET_CODES["AMEX"] == "81"
    # 과거 우리가 쓰던 잘못된 코드가 저장된 워크플로우도 살려야 한다.
    assert OVERSEAS_STOCK_MARKET_CODES["83"] == "81"


def test_all_order_executors_share_one_market_code_table():
    """사본을 두면 한 곳만 고쳐지는 사고가 난다 — 세 executor 가 같은 객체를 본다."""
    assert NewOrderNodeExecutor.STOCK_MARKET_CODES is OVERSEAS_STOCK_MARKET_CODES
    assert ModifyOrderNodeExecutor.STOCK_MARKET_CODES is OVERSEAS_STOCK_MARKET_CODES
    assert CancelOrderNodeExecutor.STOCK_MARKET_CODES is OVERSEAS_STOCK_MARKET_CODES


def test_amex_cancel_builds_valid_request():
    """회귀의 본체 — 종전에는 여기서 pydantic ValidationError 로 죽었다."""
    ls, order = _make_ls_overseas_stock(_accepted("OrdNo", 999))
    result = asyncio.run(CancelOrderNodeExecutor()._cancel_overseas_stock(
        ls=ls, order_id="321", symbol="SPCE", exchange="AMEX",
        config={}, context=_make_context(), node_id="cancel-amex",
    ))

    assert result["cancel_result"]["success"] is True
    sent = order.cosat00301.call_args.args[0]
    assert sent.OrdMktCode == "81"
    assert sent.OrdPtnCode == "08"
    assert sent.OrgOrdNo == 321

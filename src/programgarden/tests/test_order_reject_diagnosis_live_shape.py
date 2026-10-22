"""주문 거부 진단이 **LS 가 실제로 보내는 응답 모양**에 맞는지 못박는 회귀 테스트.

2026-08-19 실계좌(해외주식 COSAT00301) 실측으로 밝혀진 사실:

    LS 의 업무 거부는 ``error_msg`` 가 **비어 있고**, ``rsp_cd`` 에 오류 코드가
    실리며, 접수 블록(block2) 자체가 **없이** 온다.

executor 는 그동안 두 가지를 전제하고 있었다.
  1. 거부는 ``error_msg`` 로 온다 → 실제로는 비어 있어 그 분기를 그냥 지나쳤다.
  2. 주문번호가 없으면 "성공했는데 번호만 없음" 이다 → 그래서 **틀린 원인**
     ("장 마감이거나 브로커 지연")을 사용자에게 말했다. 예수금이 부족한 사람에게
     장이 닫혀서 그렇다고 안내하는 식이다.

이 테스트는 실측된 응답 모양을 그대로 재현해, 진단이 실제 원인을 말하는지 검증한다.
실측 코드: 02201 예수금 부족 · 02259 원주문번호 없음 · 03053 없는 종목번호 ·
03759 정정/취소 잔량 없음.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from programgarden_core import (
    ORDER_ACCEPTED_RSP_CDS,
    diagnose_missing_order_no,
    map_reject_code,
)
from programgarden.executor import CancelOrderNodeExecutor


# ---------------------------------------------------------------------------
# 실측 응답 모양 — 이 셋이 동시에 성립한다는 것이 이번 발견의 핵심
# ---------------------------------------------------------------------------

LIVE_REJECTS = [
    ("02201", "예수금 잔고가 부족합니다."),
    ("02259", "원주문번호에 해당하는 주문내용이 없습니다. 확인바랍니다."),
    ("03053", "해당 종목번호가 없습니다."),
    ("03759", "정정,취소대상 원주문수량이 없습니다. 조회로 확인바랍니다."),
]


def test_live_reject_codes_resolve_to_specific_causes():
    """실측 거부 4종이 전부 '아는 원인' 으로 해석돼야 한다."""
    for rsp_cd, rsp_msg in LIVE_REJECTS:
        info = diagnose_missing_order_no("overseas_stock", rsp_cd, rsp_msg)
        assert info.known is True, f"{rsp_cd} 가 미등재로 떨어졌다"
        assert info.rsp_cd == rsp_cd
        assert info.raw_msg == rsp_msg, "브로커 원문은 항상 보존돼야 한다"
        assert info.tip, f"{rsp_cd} 에 조치 안내가 없다"
        # 🔴 핵심 회귀: 거부인데 lifecycle 문구("장 마감/지연")로 오진하면 안 된다.
        assert "market closed" not in info.cause, (
            f"{rsp_cd}({rsp_msg}) 를 '장 마감' 으로 오진했다: {info.cause}"
        )


def test_accept_codes_still_use_lifecycle_explanation():
    """진짜 접수 코드일 때만 '번호가 안 왔다' 설명을 쓴다."""
    for rsp_cd in sorted(ORDER_ACCEPTED_RSP_CDS):
        info = diagnose_missing_order_no("overseas_stock", rsp_cd, "주문번호 없음")
        assert info.known is True
        assert "no order number returned" in info.cause


def test_empty_rsp_cd_falls_back_to_lifecycle_explanation():
    """코드가 아예 없으면 단정할 근거가 없으니 기존 설명을 유지한다."""
    info = diagnose_missing_order_no("overseas_stock", "", "주문번호 없음")
    assert "no order number returned" in info.cause


def test_unregistered_error_code_keeps_raw_msg_and_admits_it_is_unknown():
    """미등재 오류 코드는 원문만 전달하고 known=False 로 정직하게 표시한다."""
    info = diagnose_missing_order_no("overseas_stock", "09999", "알 수 없는 사유")
    assert info.known is False
    assert info.cause == "알 수 없는 사유"
    assert info.tip is None
    # 추측 원인을 지어내지 않는다.
    assert "market closed" not in info.cause


def test_map_reject_code_unchanged_for_unknown_codes():
    """기존 계약 유지 — 미등재 코드는 raw 폴백."""
    info = map_reject_code("overseas_stock", "40570", raw_msg="잔고 부족")
    assert info.known is False
    assert info.cause == "잔고 부족"


# ---------------------------------------------------------------------------
# 취소 경로 — 실측 응답 모양(error_msg 비어 있음 + block2 없음)을 그대로 먹인다
# ---------------------------------------------------------------------------

def _make_ls_cancel_overseas_stock(response):
    api = MagicMock()
    api.req_async = AsyncMock(return_value=response)
    order = MagicMock()
    order.cosat00301 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls


def _make_context():
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.send_notification = AsyncMock()
    return ctx


def _cancel(resp):
    ls = _make_ls_cancel_overseas_stock(resp)
    ctx = _make_context()
    executor = CancelOrderNodeExecutor()
    result = asyncio.run(executor._cancel_overseas_stock(
        ls=ls, order_id="29", symbol="SNDL", exchange="NASDAQ",
        config={}, context=ctx, node_id="cancel-1",
    ))
    return result, ctx


def test_cancel_reject_reports_the_real_cause_not_a_guess():
    """이미 취소된 주문 재취소(03759) — 원인이 특정돼야 한다."""
    resp = MagicMock()
    resp.error_msg = ""          # 🔴 실측: 거부인데도 비어 있다
    resp.rsp_cd = "03759"
    resp.rsp_msg = "정정,취소대상 원주문수량이 없습니다. 조회로 확인바랍니다."
    resp.block2 = None           # 🔴 실측: 접수 블록이 아예 없다

    result, ctx = _cancel(resp)
    cancel_result = result["cancel_result"]

    assert cancel_result["success"] is False
    assert result["cancelled_order_id"] == ""
    assert cancel_result["rsp_cd"] == "03759"
    reject = cancel_result["reject_info"]
    assert reject["known"] is True
    assert "already" in reject["cause"].lower()
    assert "market closed" not in cancel_result["error"]
    # 구조화 알림도 취소 노드 이름으로 나가야 한다.
    ctx.send_notification.assert_awaited()
    assert ctx.send_notification.await_args.kwargs["node_type"] == \
        "OverseasStockCancelOrderNode"


def test_cancel_reject_unknown_code_stays_honest():
    """미등재 코드면 원문만 넘기고 원인을 지어내지 않는다."""
    resp = MagicMock()
    resp.error_msg = ""
    resp.rsp_cd = "09999"
    resp.rsp_msg = "알 수 없는 사유"
    resp.block2 = None

    result, _ = _cancel(resp)
    reject = result["cancel_result"]["reject_info"]
    assert reject["known"] is False
    assert reject["raw_msg"] == "알 수 없는 사유"

"""국내주식 취소는 **부분취소**다 — 수량을 추측하면 주문이 시장에 남는다.

2026-08-19 실계좌(LS, CSPAT00801) 실측:

    2주 주문(ordno=15531)을 ``OrdQty=1`` 로 취소했더니
    ``rsp_cd=00156 "취소주문이 완료되었습니다"`` 를 받았는데
    t0425 미체결 잔량은 2 → **1** 로 남았다.

즉 국내는 해외와 의미가 다르다.

    해외주식 COSAT00301 : OrdQty=0  → 전량 취소
    국내주식 CSPAT00801 : OrdQty=N  → N주만 취소 (부분취소)

그래서 수량 미지정 시 1 로 떨어뜨리던 종전 기본값은 "취소했습니다" 라고 답한 뒤
잔량을 시장에 남기는 조용한 사고였다. 이 테스트가 그 회귀를 못박는다.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from programgarden.executor import CancelOrderNodeExecutor


def _cancel_response(ord_no: int = 15533):
    return SimpleNamespace(
        error_msg=None, rsp_cd="00156", rsp_msg="취소주문이 완료되었습니다.",
        block2=SimpleNamespace(OrdNo=ord_no),
    )


def _pending_response(rows):
    """t0425 응답 — rows = [(ordno, ordrem), ...]"""
    return SimpleNamespace(
        error_msg=None, rsp_cd="00000", rsp_msg="",
        block=[SimpleNamespace(ordno=o, ordrem=r) for o, r in rows],
    )


def _make_ls(cancel_resp, pending_resp):
    """CSPAT00801(취소) 과 t0425(미체결) 를 함께 물린 LS 목."""
    sent = {}

    def _cspat00801(body):
        sent["body"] = body
        api = MagicMock()
        api.req_async = AsyncMock(return_value=cancel_resp)
        return api

    order = MagicMock()
    order.cspat00801 = MagicMock(side_effect=_cspat00801)

    t0425_api = MagicMock()
    t0425_api.req_async = AsyncMock(return_value=pending_resp)
    accno = MagicMock()
    accno.t0425 = MagicMock(return_value=t0425_api)

    korea = MagicMock()
    korea.order = MagicMock(return_value=order)
    korea.accno = MagicMock(return_value=accno)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=korea)
    return ls, sent, accno


def _ctx():
    c = MagicMock()
    c.log = MagicMock()
    c.send_notification = AsyncMock()
    return c


def _run(ls, config, order_id="15531", symbol="A001740"):
    return asyncio.run(CancelOrderNodeExecutor()._cancel_korea_stock(
        ls=ls, order_id=order_id, symbol=symbol,
        config=config, context=_ctx(), node_id="cancel-1",
    ))


def test_explicit_quantity_is_sent_as_is():
    ls, sent, _ = _make_ls(_cancel_response(), _pending_response([]))
    result = _run(ls, {"quantity": 2})
    assert result["cancel_result"]["success"] is True
    assert sent["body"].OrdQty == 2


def test_missing_quantity_uses_the_original_orders_remaining_qty():
    """🔴 핵심 회귀 — 미지정이면 1 이 아니라 **잔량 전체**를 취소해야 한다."""
    ls, sent, _ = _make_ls(_cancel_response(), _pending_response([(15531, 2)]))
    result = _run(ls, {})
    assert result["cancel_result"]["success"] is True
    assert sent["body"].OrdQty == 2, (
        "수량 미지정인데 잔량(2) 대신 다른 값을 보냈다 — 부분취소로 잔량이 남는다"
    )


def test_t0425_is_queried_with_the_bare_six_digit_code():
    """t0425 의 expcode 는 6자리다 — 'A' 를 붙여 보내면 0건이 와서 잔량을 놓친다."""
    ls, _, accno = _make_ls(_cancel_response(), _pending_response([(15531, 2)]))
    _run(ls, {}, symbol="A001740")
    assert accno.t0425.call_args.args[0].expcode == "001740"


def test_unknown_remaining_qty_fails_loudly_instead_of_guessing_one():
    """잔량을 못 구하면 1 주만 취소하는 대신 실패로 알린다."""
    ls, sent, _ = _make_ls(_cancel_response(), _pending_response([]))
    result = _run(ls, {})
    assert result["cancel_result"]["success"] is False
    assert result["cancelled_order_id"] == ""
    assert "수량" in result["cancel_result"]["error"]
    assert "body" not in sent, "취소 수량을 모르는데 주문을 보냈다"


def test_remaining_quantity_config_still_honoured():
    ls, sent, _ = _make_ls(_cancel_response(), _pending_response([]))
    result = _run(ls, {"remaining_quantity": 7})
    assert result["cancel_result"]["success"] is True
    assert sent["body"].OrdQty == 7

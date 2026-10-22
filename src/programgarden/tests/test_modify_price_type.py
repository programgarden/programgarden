"""해외주식 정정(COSAT00311) 호가유형 — 스키마의 ``price_type`` 를 실행부가 존중한다.

배경(회귀 방지):
    OverseasStockModifyOrderNode 스키마는 ``price_type: Literal["limit","market"]``
    를 노출한다(core/programgarden_core/nodes/order.py:784). 그런데 정정 실행부는
    ``config.get("price_type_code", "00")`` 로 **LS 원시코드만** 읽어 ``price_type``
    을 통째 무시했다 — ``price_type="market"`` 로 정정을 걸어도 조용히 지정가('00')로
    나갔다(지정가 리프라이스만 우연히 동작). 잔재 ``config.get("side","buy")`` 도 함께
    있었다(브로커 요청/원장 어디에도 안 쓰이는데 실행부가 읽고 있었다).

    SDK 확인(2026-09-24): COSAT00311InBlock1.OrdprcPtnCode 는 '00'=지정가,
    '03'=시장가 를 문서화한다(examples=["00","03"];
    finance/.../COSAT00311/blocks.py:94-104). 즉 정정 TR 은 시장가를 지원하므로
    'market' 은 신규주문(COSAT00301)과 같은 '03' 으로 매핑한다(코드 지어내기 아님 —
    NewOrderNodeExecutor.STOCK_PRICE_TYPE_CODES 를 그대로 재사용).

    라이브 키 없이 mock LS 응답으로 와이어의 OrdprcPtnCode 를 검증한다.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden_core.exceptions import ValidationError
from programgarden.executor import ModifyOrderNodeExecutor, NewOrderNodeExecutor


def _make_context(side="buy"):
    """정정 경로가 방향/미변경 필드를 승계할 수 있도록 원 주문 원장 행을 흉내낸다."""
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.find_workflow_order = MagicMock(return_value={
        "order_no": "12345", "order_date": "20260924", "symbol": "AAPL",
        "exchange": "NASDAQ", "side": side, "quantity": 7, "price": 149.0,
        "node_id": "order-node", "job_id": "job",
    })
    return ctx


def _make_ls(order_no="67890"):
    """ls.overseas_stock().주문().cosat00311(...).req_async() -> 정상 응답 체인."""
    resp = MagicMock()
    resp.error_msg = None
    resp.rsp_msg = "정상처리"
    block2 = MagicMock()
    block2.OrdNo = order_no
    resp.block2 = block2

    api = MagicMock()
    api.req_async = AsyncMock(return_value=resp)
    order = MagicMock()
    order.cosat00311 = MagicMock(return_value=api)
    stock = MagicMock()
    stock.주문 = MagicMock(return_value=order)
    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=stock)
    return ls


def _wire(ls):
    """cosat00311 에 실제로 넘어간 COSAT00311InBlock1."""
    return ls.overseas_stock().주문().cosat00311.call_args.args[0]


def _run(config):
    ls = _make_ls()
    ctx = _make_context()
    result = asyncio.run(ModifyOrderNodeExecutor()._modify_overseas_stock(
        ls=ls,
        original_order_id="12345",
        symbol="AAPL",
        exchange="NASDAQ",
        new_quantity=10,
        new_price=150.0,
        config=config,
        context=ctx,
        node_id="modify-node",
    ))
    return result, ls


# ---------------------------------------------------------------------------
# (1) 지정가 리프라이스 — price_type='limit' → OrdprcPtnCode='00'
# ---------------------------------------------------------------------------
def test_price_type_limit_maps_to_00():
    result, ls = _run({"price_type": "limit"})
    assert result["modify_result"]["success"] is True, result
    assert _wire(ls).OrdprcPtnCode == "00"


def test_no_price_fields_defaults_to_00():
    """둘 다 없으면 종전 동작 유지 — 지정가('00')."""
    result, ls = _run({})
    assert result["modify_result"]["success"] is True
    assert _wire(ls).OrdprcPtnCode == "00"


def test_side_in_config_does_not_change_price_type():
    """잔재였던 side 는 호가유형에 영향을 주지 않는다(여전히 기본 '00')."""
    result, ls = _run({"side": "sell"})
    assert result["modify_result"]["success"] is True
    assert _wire(ls).OrdprcPtnCode == "00"


# ---------------------------------------------------------------------------
# (4) 시장가 정정 — SDK finding: COSAT00311 이 '03' 지원 → price_type='market' 매핑
# ---------------------------------------------------------------------------
def test_price_type_market_maps_to_03():
    result, ls = _run({"price_type": "market"})
    assert result["modify_result"]["success"] is True, result
    assert _wire(ls).OrdprcPtnCode == "03"
    # 코드를 지어내지 않았다 — 신규주문 실행부의 매핑을 그대로 재사용한다.
    assert NewOrderNodeExecutor.STOCK_PRICE_TYPE_CODES["market"] == "03"


# ---------------------------------------------------------------------------
# (2) price_type_code 명시 오버라이드가 이긴다(하위호환)
# ---------------------------------------------------------------------------
def test_explicit_price_type_code_override_wins_market():
    result, ls = _run({"price_type_code": "03"})
    assert result["modify_result"]["success"] is True
    assert _wire(ls).OrdprcPtnCode == "03"


def test_explicit_price_type_code_alone_limit():
    result, ls = _run({"price_type_code": "00"})
    assert _wire(ls).OrdprcPtnCode == "00"


def test_agreeing_price_type_and_code_passes():
    result, ls = _run({"price_type": "market", "price_type_code": "03"})
    assert result["modify_result"]["success"] is True
    assert _wire(ls).OrdprcPtnCode == "03"


# ---------------------------------------------------------------------------
# (3) 충돌 — price_type vs price_type_code 가 다른 유형을 가리키면 거부
# ---------------------------------------------------------------------------
def test_conflicting_price_type_and_code_rejected():
    with pytest.raises(ValidationError) as ei:
        _run({"price_type": "market", "price_type_code": "00"})
    assert ei.value.field == "price_type_code"
    # 와이어에 아무것도 안 나갔다(정정을 보내기 전에 막힌다).


# ---------------------------------------------------------------------------
# 순수 리졸버 단위 테스트 (_resolve_stock_modify_price_type_code)
# ---------------------------------------------------------------------------
def test_resolver_limit():
    assert ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code(
        {"price_type": "limit"}, "n") == "00"


def test_resolver_market_reuses_new_order_mapping():
    code = ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code(
        {"price_type": "MARKET"}, "n")  # 대소문자 무관
    assert code == NewOrderNodeExecutor.STOCK_PRICE_TYPE_CODES["market"] == "03"


def test_resolver_neither_defaults_00():
    assert ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code({}, "n") == "00"


def test_resolver_unsupported_price_type_raises():
    with pytest.raises(ValidationError) as ei:
        ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code(
            {"price_type": "LOO"}, "n")
    assert ei.value.field == "price_type"


def test_resolver_conflict_raises():
    with pytest.raises(ValidationError) as ei:
        ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code(
            {"price_type": "limit", "price_type_code": "03"}, "n")
    assert ei.value.field == "price_type_code"


def test_resolver_explicit_code_only_returned_verbatim():
    # price_type 없이 원시코드만 주면 그대로 반환(하위호환 오버라이드).
    assert ModifyOrderNodeExecutor()._resolve_stock_modify_price_type_code(
        {"price_type_code": "03"}, "n") == "03"

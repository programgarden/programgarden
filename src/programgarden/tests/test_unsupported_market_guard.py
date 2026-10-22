"""지원하지 않는 시장(장외/OTC 등) 종목은 브로커를 부르기 전에 막고 사유를 알린다.

배경 — 2026-09-14 prod 실계좌. 보유 종목 ZOMDF 의 잔고 거래소가 `85` 로 왔는데 엔진이
그것을 조용히 `82`(나스닥)로 바꿔 주문을 보냈고, LS 가 `03053 "해당 종목번호가 없습니다"`
로 거부했다. 사용자에게는 **종목을 잘못 쓴 것처럼** 보였다. LS증권 유선 확인 결과 OTC
종목은 API 주문 자체가 불가하고 전화로만 거래된다.
"""
import pytest

from programgarden_core.models import (
    LS_OVERSEAS_DESK_PHONE,
    OVERSEAS_STOCK_ORDER_MARKET_CODES,
    UNSUPPORTED_MARKET_RSP_CD,
    diagnose_missing_order_no,
    looks_like_otc_ticker,
    unsupported_market_reject,
)
from programgarden.executor import resolve_overseas_stock_order_market


@pytest.mark.parametrize(
    "raw,expected",
    [("NYSE", "81"), ("AMEX", "81"), ("NASDAQ", "82"), ("81", "81"), ("82", "82"), ("nasdaq", "82")],
)
def test_supported_markets_resolve(raw, expected):
    code, err = resolve_overseas_stock_order_market(raw)
    assert (code, err) == (expected, None)


@pytest.mark.parametrize("raw", ["85", "83", "OTC", "TSE", "", None])
def test_unsupported_market_is_blocked_not_defaulted(raw):
    """모르는 코드는 82 로 떨어지지 않는다 — 이것이 이번 사고의 뿌리였다."""
    code, err = resolve_overseas_stock_order_market(raw)
    assert code is None, f"{raw!r} 이 조용히 {code} 로 폴백됐다"
    assert err, "사유 없이 막으면 안 된다"


def test_block_reason_names_the_market_and_points_to_ls():
    _, err = resolve_overseas_stock_order_market("85")
    assert "85" in err, "어떤 시장인지 사용자가 알아야 한다"
    assert "LS증권" in err, "처리 불가 종목은 LS증권 문의로 안내해야 한다"


def test_reject_diagnostic_says_do_not_retry():
    reject = unsupported_market_reject("85", "ZOMDF")
    assert reject.rsp_cd == UNSUPPORTED_MARKET_RSP_CD
    assert reject.rsp_cd.startswith("PG_"), "브로커가 준 코드가 아님이 드러나야 한다"
    assert reject.retry.value == "do_not_retry", "성공할 수 없는 요청을 재시도로 안내하면 안 된다"
    assert reject.known is True
    assert "85" in reject.cause
    assert "LS Securities" in (reject.tip or "")


def test_03053_tip_no_longer_blames_the_ticker_alone():
    """보유 종목에서 난 03053 은 '철자 확인' 이 아니라 거래 불가 가능성을 알려야 한다."""
    reject = diagnose_missing_order_no("overseas_stock", "03053", "해당 종목번호가 없습니다.")
    assert reject.known is True
    tip = (reject.tip or "")
    assert "OTC" in tip and "LS Securities" in tip, tip


def test_order_market_table_has_no_third_value():
    """COSAT00301 OrdMktCode 는 Literal["81","82"] — 세 번째 값을 추측해 넣지 않는다."""
    assert set(OVERSEAS_STOCK_ORDER_MARKET_CODES.values()) == {"81", "82"}


# ── LS증권이 알려준 실무 정보 (2026-09-14) ──────────────────────────────────
# OTC 종목은 ☎ 02-3779-8888 로 전화해 매도를 요청해야 한다. 티커가 5자이고 F 로
# 끝나면 보통 OTC 지만 **항상 맞는 규칙은 아니다** — 차단 판단에 쓰면 안 된다.


def test_block_reason_carries_the_ls_desk_phone():
    _, err = resolve_overseas_stock_order_market("85", "ZOMDF")
    assert LS_OVERSEAS_DESK_PHONE in err, "전화로만 팔 수 있는 종목이면 번호를 알려줘야 한다"


def test_reject_tip_carries_the_ls_desk_phone():
    assert LS_OVERSEAS_DESK_PHONE in (unsupported_market_reject("85", "ZOMDF").tip or "")
    assert LS_OVERSEAS_DESK_PHONE in (
        diagnose_missing_order_no("overseas_stock", "03053", "해당 종목번호가 없습니다.").tip or ""
    )


@pytest.mark.parametrize("sym", ["ZOMDF", "ABCDF", "zomdf"])
def test_otc_ticker_heuristic_matches(sym):
    assert looks_like_otc_ticker(sym) is True


@pytest.mark.parametrize("sym", ["NIO", "MARA", "SNDL", "AAPL", "ZOMD", "ZOMDFX", "", None, "ZOM1F"])
def test_otc_ticker_heuristic_does_not_overmatch(sym):
    assert looks_like_otc_ticker(sym) is False


def test_otc_hint_only_appears_for_matching_tickers():
    _, otc = resolve_overseas_stock_order_market("85", "ZOMDF")
    _, other = resolve_overseas_stock_order_market("85", "NIO")
    assert "F 로 끝나" in otc
    assert "F 로 끝나" not in other, "규칙이 아닌 경험칙을 단정해서 말하면 안 된다"


def test_heuristic_never_blocks_a_supported_market():
    """5자 F 티커라도 거래소가 지원 대상이면 주문은 나가야 한다 — 경험칙은 차단 기준이 아니다."""
    code, err = resolve_overseas_stock_order_market("NASDAQ", "ABCDF")
    assert (code, err) == ("82", None)

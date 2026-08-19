"""Phase 1 unit tests for src/core/programgarden_core/models/order_diagnostics.py.

Covers map_reject_code fallback / mapped-hit / unknown-market behavior, plus
OrderRejectInfo and EmptyOrderReason shape and serialization. Codes are
registered only after live verification; the overseas-stock table now holds four
codes measured on a real account (2026-08-19), while the futures / Korea tables
are still empty. The mapped-hit case injects a code via monkeypatch so it stays
independent of whichever codes happen to be registered.
"""
from __future__ import annotations

import re

from programgarden_core.models.order_diagnostics import (
    EmptyOrderReason,
    OrderRejectInfo,
    OVERSEAS_STOCK_REJECT_CODES,
    OVERSEAS_FUTURES_REJECT_CODES,
    KOREA_STOCK_REJECT_CODES,
    RetryAdvice,
    _MARKET_TABLES,
    diagnose_missing_order_no,
    map_reject_code,
)


# ---------------------------------------------------------------------------
# Tables hold live-collected codes only (no guessing)
# ---------------------------------------------------------------------------

# Registered from a real LS overseas-stock account on 2026-08-19 by deliberately
# triggering each rejection. Pinned here so a future guess-based addition fails.
LIVE_VERIFIED_OVERSEAS_STOCK_CODES = {"02201", "02259", "03053", "03759"}

# Registered from a real LS Korea-stock account on 2026-08-19 the same way
# (CSPAT00601 new order / CSPAT00801 cancel, each rejection deliberately
# triggered). Pinned so a future guess-based addition fails.
LIVE_VERIFIED_KOREA_STOCK_CODES = {"01524", "03056", "03181"}

_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")


def test_overseas_stock_table_holds_exactly_the_live_verified_codes() -> None:
    assert set(OVERSEAS_STOCK_REJECT_CODES) == LIVE_VERIFIED_OVERSEAS_STOCK_CODES


def test_registered_entries_carry_english_cause_and_tip() -> None:
    for code, entry in OVERSEAS_STOCK_REJECT_CODES.items():
        cause, tip = entry.get("cause", ""), entry.get("tip", "")
        assert cause.strip(), f"{code} has no cause"
        assert tip.strip(), f"{code} has no tip"
        # ``cause``/``tip`` are the chatbot-facing strings and must stay English —
        # the raw Korean broker text travels separately in ``raw_msg``. Checked
        # by looking for Hangul rather than ``isascii()``, which would also
        # reject ordinary English typography such as an em dash.
        assert not _HANGUL.search(cause), f"{code} cause contains Korean: {cause!r}"
        assert not _HANGUL.search(tip), f"{code} tip contains Korean: {tip!r}"


def test_korea_stock_table_holds_exactly_the_live_verified_codes() -> None:
    assert set(KOREA_STOCK_REJECT_CODES) == LIVE_VERIFIED_KOREA_STOCK_CODES


def test_korea_entries_carry_english_cause_and_tip() -> None:
    for code, entry in KOREA_STOCK_REJECT_CODES.items():
        cause, tip = entry.get("cause", ""), entry.get("tip", "")
        assert cause.strip(), f"{code} has no cause"
        assert tip.strip(), f"{code} has no tip"
        assert not _HANGUL.search(cause), f"{code} cause contains Korean: {cause!r}"
        assert not _HANGUL.search(tip), f"{code} tip contains Korean: {tip!r}"


def test_unmeasured_tables_stay_empty() -> None:
    # Overseas-futures rejects have not been live-collected yet. That table must
    # stay empty rather than be filled in from the spec.
    assert OVERSEAS_FUTURES_REJECT_CODES == {}


# ---------------------------------------------------------------------------
# (a) empty table -> known=False raw fallback, tip=None
# ---------------------------------------------------------------------------


def test_unmapped_code_falls_back_to_raw_msg() -> None:
    info = map_reject_code("overseas_stock", "40570", raw_msg="잔고 부족")
    assert info.known is False
    assert info.cause == "잔고 부족"
    assert info.tip is None
    assert info.rsp_cd == "40570"
    assert info.raw_msg == "잔고 부족"


def test_unmapped_code_without_raw_msg_uses_synthetic_cause() -> None:
    info = map_reject_code("overseas_stock", "99999")
    assert info.known is False
    assert info.tip is None
    assert "99999" in info.cause
    assert "no diagnostic mapping" in info.cause
    assert info.raw_msg == ""


# ---------------------------------------------------------------------------
# (b) injected code -> known=True, mapped cause/tip
# ---------------------------------------------------------------------------


def test_mapped_code_returns_known_diagnostic(monkeypatch) -> None:
    monkeypatch.setitem(
        OVERSEAS_STOCK_REJECT_CODES,
        "40570",
        {
            "cause": "Insufficient buying power for this order.",
            "tip": "Reduce order quantity or deposit additional funds.",
        },
    )
    info = map_reject_code("overseas_stock", "40570", raw_msg="raw broker text")
    assert info.known is True
    assert info.cause == "Insufficient buying power for this order."
    assert info.tip == "Reduce order quantity or deposit additional funds."
    # raw_msg is always preserved alongside the mapped cause.
    assert info.raw_msg == "raw broker text"


def test_mapped_code_empty_cause_falls_back_to_raw_msg(monkeypatch) -> None:
    monkeypatch.setitem(
        OVERSEAS_STOCK_REJECT_CODES,
        "40571",
        {"cause": "", "tip": ""},
    )
    info = map_reject_code("overseas_stock", "40571", raw_msg="broker said no")
    # Found in the table -> known stays True even though cause was blank.
    assert info.known is True
    assert info.cause == "broker said no"
    # Empty tip string is normalized to None.
    assert info.tip is None


# ---------------------------------------------------------------------------
# (c) unknown market -> safe raw fallback (known=False)
# ---------------------------------------------------------------------------


def test_unknown_market_falls_back_safely() -> None:
    info = map_reject_code("crypto_perp", "12345", raw_msg="not supported")
    assert info.known is False
    assert info.cause == "not supported"
    assert info.tip is None
    assert info.rsp_cd == "12345"


def test_success_code_handled_defensively() -> None:
    # Callers filter "00000", but the mapper must not blow up if it leaks in.
    info = map_reject_code("overseas_stock", "00000", raw_msg="")
    assert info.known is False
    assert "00000" in info.cause


# ---------------------------------------------------------------------------
# (d) non-str inputs are cast defensively (e.g. int OrdNo, None raw_msg)
# ---------------------------------------------------------------------------


def test_non_str_rsp_cd_does_not_raise() -> None:
    # Korea OrdNo is int; a caller may pass it straight through. Must cast.
    # A non-zero int is preserved as its string form.
    info = map_reject_code("korea_stock", 12345, raw_msg="rejected")  # type: ignore[arg-type]
    assert info.known is False
    assert info.rsp_cd == "12345"
    assert info.cause == "rejected"
    assert info.raw_msg == "rejected"


def test_zero_int_rsp_cd_normalizes_to_empty() -> None:
    # `str(rsp_cd or "")` treats falsy 0 as empty — defensive, never raises.
    info = map_reject_code("korea_stock", 0, raw_msg="rejected")  # type: ignore[arg-type]
    assert info.known is False
    assert info.rsp_cd == ""
    assert info.cause == "rejected"


def test_none_raw_msg_does_not_raise() -> None:
    # Mocked LS responses may carry rsp_cd=None / error_msg=None.
    info = map_reject_code("overseas_futures", None, raw_msg=None)  # type: ignore[arg-type]
    assert info.known is False
    assert info.rsp_cd == ""
    assert info.raw_msg == ""
    # Synthetic cause still produced without raising.
    assert "no diagnostic mapping" in info.cause


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_order_reject_info_model_dump() -> None:
    info = OrderRejectInfo(
        rsp_cd="40570",
        cause="Insufficient buying power.",
        tip="Deposit more funds.",
        raw_msg="잔고 부족",
        known=True,
    )
    dumped = info.model_dump()
    assert dumped == {
        "rsp_cd": "40570",
        "cause": "Insufficient buying power.",
        "tip": "Deposit more funds.",
        "raw_msg": "잔고 부족",
        # 미지정 시 UNKNOWN — 관측 안 된 코드를 "재시도해도 된다"로 기본값 두면
        # 챗봇이 주문을 중복 발주할 수 있다. 모르면 모른다고 말한다.
        "retry": "unknown",
        "known": True,
    }


def test_order_reject_info_forbids_extra_fields() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OrderRejectInfo(
            rsp_cd="1",
            cause="c",
            raw_msg="m",
            known=False,
            cause_ko="금지",  # extra="forbid"
        )


def test_empty_order_reason_values() -> None:
    assert EmptyOrderReason.NO_SIGNAL.value == "no_signal"
    assert EmptyOrderReason.FETCH_FAILED.value == "fetch_failed"
    assert EmptyOrderReason.NO_SYMBOL.value == "no_symbol"
    # str-Enum: comparable to its string value.
    assert EmptyOrderReason.NO_SIGNAL == "no_signal"


def test_empty_order_reason_serializes_as_string() -> None:
    payload = {"reason": EmptyOrderReason.FETCH_FAILED}
    # str subclass serializes transparently in dicts / JSON.
    assert payload["reason"] == "fetch_failed"


# ---------------------------------------------------------------------------
# import smoke
# ---------------------------------------------------------------------------


def test_import_smoke_from_module() -> None:
    from programgarden_core.models.order_diagnostics import (  # noqa: F401
        map_reject_code as _m,
        EmptyOrderReason as _e,
        OrderRejectInfo as _o,
    )


def test_import_smoke_from_top_level() -> None:
    from programgarden_core import (  # noqa: F401
        OrderRejectInfo as _o,
        EmptyOrderReason as _e,
        map_reject_code as _m,
    )


# ---------------------------------------------------------------------------
# 재시도 판단 (RetryAdvice) — 챗봇이 "다시 걸까 / 고치라고 할까 / 기다릴까"를
# 프로즈에서 추론하지 않고 필드 하나로 알 수 있어야 한다.
# ---------------------------------------------------------------------------

def test_measured_codes_carry_a_retry_decision() -> None:
    """실측 등재된 코드는 재시도 판단을 함께 준다."""
    # 같은 요청을 다시 보내면 같은 답이 오는 것들
    for market, code in (
        ("overseas_stock", "02259"),   # 그 원주문번호가 없다
        ("overseas_stock", "03053"),   # 없는 종목
        ("overseas_stock", "03759"),   # 정정/취소할 잔량 없음
        ("korea_stock", "01524"),      # 없는 종목
        ("korea_stock", "03056"),      # 그 원주문번호가 없다
    ):
        assert map_reject_code(market, code).retry is RetryAdvice.DO_NOT_RETRY, code

    # 사용자가 뭔가 바꾸면 통하는 것들
    assert map_reject_code("overseas_stock", "02201").retry is RetryAdvice.RETRY_AFTER_FIX
    assert map_reject_code("korea_stock", "03181").retry is RetryAdvice.RETRY_AFTER_FIX


def test_unobserved_code_never_claims_it_is_retryable() -> None:
    """🔴 관측 안 된 코드는 UNKNOWN — 챗봇이 raw_msg 를 읽고 판단하라는 뜻이다.

    여기에 "재시도 가능" 기본값을 두면, 접수됐는지 알 수 없는 주문을 다시 보내
    **중복 발주**가 난다. 모르면 모른다고 말하는 쪽이 언제나 싸다.
    """
    info = map_reject_code("korea_stock", "03591", raw_msg="입력일자를 잘못 입력하셨습니다")
    assert info.known is False
    assert info.retry is RetryAdvice.UNKNOWN
    assert info.raw_msg == "입력일자를 잘못 입력하셨습니다"   # 증권사 원문이 그대로 실린다
    assert info.rsp_cd == "03591"


def test_accepted_but_unnumbered_order_is_never_retried() -> None:
    """접수는 됐는데 번호가 없는 상태에서 재전송하면 살아 있는 주문이 중복된다."""
    info = diagnose_missing_order_no("korea_stock", "00040", raw_msg="")
    assert info.known is True
    assert info.retry is RetryAdvice.DO_NOT_RETRY


def test_every_registered_code_declares_a_retry_decision() -> None:
    """등재하면서 재시도 판단을 빠뜨리면 조용히 UNKNOWN 이 된다 — 그걸 막는다."""
    for market, table in _MARKET_TABLES.items():
        for code, entry in table.items():
            assert entry.get("retry"), f"{market}/{code} 에 retry 가 없다"
            RetryAdvice(entry["retry"])   # 오타면 여기서 터진다

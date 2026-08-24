"""소수점(fractional) 수량이 주문 정규화·진단에서 조용히 사라지지 않는지 검증.

prod 2026-08-24 실측: IBM 0.847972주(소수점 잔고) 보유 계좌에서 SOXL 전량매도가
잔고조회 단계에서 죽었다. 엔진 쪽 결함은 두 가지였다 —
(1) _normalize_order 의 int() 절단이 소수점 전량매도 주문을 **조용히** 소멸시킴
(2) 소수점만 보유한 경우 사유 없는 no-op ("주문할 종목이 없습니다")
"""
import pytest

from programgarden_core.models.order_diagnostics import EmptyOrderReason
from programgarden.executor import NewOrderNodeExecutor, _qty_num


def _executor() -> NewOrderNodeExecutor:
    # _normalize_order / _diagnose_empty_reason 은 인스턴스 상태를 쓰지 않는다.
    return NewOrderNodeExecutor.__new__(NewOrderNodeExecutor)


class TestQtyNum:
    def test_integer_stays_int(self):
        assert _qty_num(16) == 16
        assert isinstance(_qty_num(16), int)
        assert isinstance(_qty_num(16.0), int)
        assert isinstance(_qty_num("16"), int)

    def test_fractional_preserved(self):
        assert _qty_num(0.847972) == pytest.approx(0.847972)
        assert _qty_num("0.847972") == pytest.approx(0.847972)

    def test_garbage_defaults(self):
        assert _qty_num(None) == 0
        assert _qty_num("abc") == 0
        assert _qty_num("abc", default=7) == 7


class TestNormalizeOrderFractional:
    def test_fractional_floored_with_remainder(self):
        out = _executor()._normalize_order(
            {"symbol": "SOXL", "quantity": 16.847972, "price": 10.0}, {}
        )
        assert out is not None
        assert out["quantity"] == 16
        assert out["fractional_remainder"] == pytest.approx(0.847972)

    def test_integer_has_no_remainder_key(self):
        out = _executor()._normalize_order(
            {"symbol": "SOXL", "quantity": 16, "price": 10.0}, {}
        )
        assert out is not None
        assert out["quantity"] == 16
        assert "fractional_remainder" not in out

    def test_fractional_only_returns_none(self):
        out = _executor()._normalize_order(
            {"symbol": "IBM", "quantity": 0.847972, "price": 10.0}, {}
        )
        assert out is None


class TestDiagnoseFractionalOnly:
    def test_fractional_only_reason(self):
        reason, detail = _executor()._diagnose_empty_reason(
            {"symbol": "IBM", "quantity": 0.847972, "price": 10.0}, {}, None, None
        )
        assert reason == EmptyOrderReason.FRACTIONAL_ONLY
        assert "0.847972" in detail
        assert "IBM" in detail

    def test_empty_order_still_no_symbol(self):
        reason, _ = _executor()._diagnose_empty_reason(None, {}, None, None)
        assert reason == EmptyOrderReason.NO_SYMBOL

    def test_fractional_only_message_registered(self):
        assert (
            EmptyOrderReason.FRACTIONAL_ONLY.value
            in NewOrderNodeExecutor._EMPTY_ORDER_MESSAGES
        )

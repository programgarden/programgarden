"""
compute_futures_pnl_rate 공유 헬퍼 테스트 (E2)

REST 잔고 직렬화와 실시간 트래커가 동일한 수익률 값을 내도록 하는
단일 진실 공급원. 승수(contract multiplier)와 무관하게 명목가 대비 수익률.
"""

from decimal import Decimal

import pytest

from programgarden_finance.ls.overseas_futureoption.extension.calculator import (
    compute_futures_pnl_rate,
)


class TestComputeFuturesPnlRate:

    def test_long_gain_float(self):
        rate = compute_futures_pnl_rate(8547.67, 8601.0, is_long=True)
        assert rate == pytest.approx((8601.0 - 8547.67) / 8547.67 * 100)
        assert rate > 0

    def test_long_loss_float(self):
        rate = compute_futures_pnl_rate(100.0, 90.0, is_long=True)
        assert rate == pytest.approx(-10.0)

    def test_short_sign_reversed(self):
        # 숏: 현재가 > 진입가 → 손실(음수)
        long_rate = compute_futures_pnl_rate(100.0, 110.0, is_long=True)
        short_rate = compute_futures_pnl_rate(100.0, 110.0, is_long=False)
        assert long_rate == pytest.approx(10.0)
        assert short_rate == pytest.approx(-10.0)

    def test_short_gain(self):
        # 숏: 현재가 < 진입가 → 이익(양수)
        rate = compute_futures_pnl_rate(100.0, 90.0, is_long=False)
        assert rate == pytest.approx(10.0)

    def test_multiplier_independence(self):
        # 승수는 계산에 들어가지 않는다 — 가격만으로 동일 결과
        rate = compute_futures_pnl_rate(8547.67, 8601.0, is_long=True)
        assert rate == pytest.approx(0.6239, abs=1e-3)

    def test_decimal_inputs_return_float(self):
        # 반환 타입은 float 로 일원화 (Decimal 입력이어도)
        rate = compute_futures_pnl_rate(Decimal("100"), Decimal("110"), is_long=True)
        assert isinstance(rate, float)
        assert rate == pytest.approx(10.0)

    def test_mixed_decimal_float_no_typeerror(self):
        # Decimal 진입가 + float 현재가 혼합 — TypeError 없이 계산
        rate = compute_futures_pnl_rate(Decimal("100"), 110.0, is_long=True)
        assert rate == pytest.approx(10.0)
        rate2 = compute_futures_pnl_rate(100.0, Decimal("90"), is_long=True)
        assert rate2 == pytest.approx(-10.0)

    def test_non_numeric_inputs_return_zero(self):
        assert compute_futures_pnl_rate("abc", 100.0, is_long=True) == 0.0

    def test_zero_entry_returns_zero(self):
        assert compute_futures_pnl_rate(0.0, 8601.0, is_long=True) == 0.0
        assert compute_futures_pnl_rate(Decimal("0"), Decimal("8601"), is_long=True) == Decimal("0")

    def test_negative_entry_returns_zero(self):
        assert compute_futures_pnl_rate(-5.0, 8601.0, is_long=True) == 0.0

    def test_none_inputs_return_zero(self):
        assert compute_futures_pnl_rate(None, 100.0, is_long=True) == 0.0
        assert compute_futures_pnl_rate(100.0, None, is_long=True) == 0.0


def test_futures_position_item_has_is_long_not_side():
    """MAJOR-1 회귀 가드: FuturesPositionItem 은 side 속성이 없고 is_long 만 있다.

    과거 executor 실시간 콜백이 pos_item.side(부재) 를 읽어 숏을 항상 "long" 으로
    오라벨 → 승수 역산 부호가 뒤집혀 폴백됐다. 실시간 dict 는 is_long 으로 방향을
    표기해야 한다.
    """
    from programgarden_finance.ls.overseas_futureoption.extension.models import (
        FuturesPositionItem,
    )
    short = FuturesPositionItem(symbol="HSIQ26", is_long=False)
    assert not hasattr(short, "side")
    assert short.is_long is False
    # 실시간 콜백이 쓰는 매핑 규약
    assert ("long" if getattr(short, "is_long", True) else "short") == "short"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

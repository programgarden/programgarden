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

    def test_decimal_inputs_preserve_type(self):
        rate = compute_futures_pnl_rate(Decimal("100"), Decimal("110"), is_long=True)
        assert isinstance(rate, Decimal)
        assert rate == Decimal("10")

    def test_zero_entry_returns_zero(self):
        assert compute_futures_pnl_rate(0.0, 8601.0, is_long=True) == 0.0
        assert compute_futures_pnl_rate(Decimal("0"), Decimal("8601"), is_long=True) == Decimal("0")

    def test_negative_entry_returns_zero(self):
        assert compute_futures_pnl_rate(-5.0, 8601.0, is_long=True) == 0.0

    def test_none_inputs_return_zero(self):
        assert compute_futures_pnl_rate(None, 100.0, is_long=True) == 0.0
        assert compute_futures_pnl_rate(100.0, None, is_long=True) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

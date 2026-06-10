"""
TrailingStop (HWM 트레일링 스탑) 플러그인 테스트

v2.1.0: trail_percent 고정 % 모드 + data close 기반 HWM 자가 갱신 검증
"""

from decimal import Decimal

import pytest
from programgarden_community.plugins.trailing_stop import (
    trailing_stop_condition,
    TRAILING_STOP_SCHEMA,
    risk_features,
)


class MockHWM:
    def __init__(self, hwm_price, current_price, position_avg_price, drawdown_pct):
        self.hwm_price = Decimal(str(hwm_price))
        self.current_price = Decimal(str(current_price))
        self.position_avg_price = Decimal(str(position_avg_price))
        self.drawdown_pct = Decimal(str(drawdown_pct))


class MockRiskTracker:
    """update_price 가 실제 WorkflowRiskTracker 와 동일한 HWM 전진/드로다운 갱신을 수행"""

    def __init__(self, hwm_data=None):
        self._hwm_data = hwm_data or {}
        self.update_calls = []

    def get_hwm(self, symbol):
        return self._hwm_data.get(symbol)

    def update_price(self, symbol, exchange, price, timestamp=None):
        self.update_calls.append((symbol, exchange, price))
        state = self._hwm_data.get(symbol)
        if state is None:
            return None  # 미등록 심볼 — 실제 tracker 와 동일
        dec_price = Decimal(str(price))
        state.current_price = dec_price
        if dec_price > state.hwm_price:
            state.hwm_price = dec_price
            state.drawdown_pct = Decimal("0")
        elif state.hwm_price > 0:
            state.drawdown_pct = (state.hwm_price - dec_price) / state.hwm_price * 100
        return state


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestSchema:
    def test_schema_id(self):
        assert TRAILING_STOP_SCHEMA.id == "TrailingStop"

    def test_schema_version_bumped(self):
        assert TRAILING_STOP_SCHEMA.version == "2.1.0"

    def test_trail_percent_field_exists(self):
        assert "trail_percent" in TRAILING_STOP_SCHEMA.fields_schema
        assert TRAILING_STOP_SCHEMA.fields_schema["trail_percent"]["default"] == 0.0

    def test_risk_features(self):
        assert "hwm" in risk_features


class TestFixedTrailPercent:
    """trail_percent 고정 % 모드"""

    @pytest.mark.asyncio
    async def test_sell_when_drawdown_reaches_trail_percent(self):
        # 고점 100 → 현재가 94 (drawdown 6%) → 5% 고정 트레일링 발동
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=100.0, current_price=94.0,
                            position_avg_price=90.0, drawdown_pct=6.0),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 94.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["result"] is True
        assert result["passed_symbols"] == [{"symbol": "AAPL", "exchange": "NASDAQ"}]
        sr = result["symbol_results"][0]
        assert sr["signal"] == "sell"
        assert sr["threshold_pct"] == 5.0

    @pytest.mark.asyncio
    async def test_sell_at_exact_trail_percent_boundary(self):
        # 고정 모드는 경계 포함(>=): 정확히 -5% 도달 시 매도
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=100.0, current_price=95.0,
                            position_avg_price=90.0, drawdown_pct=5.0),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 95.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["result"] is True
        assert result["symbol_results"][0]["signal"] == "sell"

    @pytest.mark.asyncio
    async def test_hold_below_trail_percent(self):
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=100.0, current_price=97.0,
                            position_avg_price=90.0, drawdown_pct=3.0),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 97.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["result"] is False
        assert result["symbol_results"][0]["signal"] == "hold"

    @pytest.mark.asyncio
    async def test_fixed_mode_ignores_profit_scaling(self):
        # 수익이 작아도(스케일링이면 1% 바닥) 고정 5% 전까지는 hold 유지
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=101.0, current_price=98.0,
                            position_avg_price=100.0, drawdown_pct=2.97),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 98.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        # 스케일링 모드였다면 threshold=max(1%*0.3, 1.0)=1.0 < 2.97 → sell
        # 고정 모드는 threshold=5.0 > 2.97 → hold
        assert result["symbol_results"][0]["signal"] == "hold"
        assert result["symbol_results"][0]["threshold_pct"] == 5.0


class TestHwmSelfUpdate:
    """data close 기반 HWM 자가 갱신"""

    @pytest.mark.asyncio
    async def test_close_advances_hwm_before_evaluation(self):
        # 트래커 HWM 이 stale(100)이어도 close=110 이면 HWM 110 으로 전진 → drawdown 0 → hold
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=100.0, current_price=100.0,
                            position_avg_price=90.0, drawdown_pct=0.0),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 110.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert tracker.update_calls == [("AAPL", "NASDAQ", 110.0)]
        assert result["symbol_results"][0]["signal"] == "hold"
        assert float(tracker.get_hwm("AAPL").hwm_price) == 110.0

    @pytest.mark.asyncio
    async def test_drop_after_advance_triggers_from_new_hwm(self):
        # 고점 120 등록 후 close=113 → drawdown 5.83% >= 5% → sell
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=120.0, current_price=120.0,
                            position_avg_price=100.0, drawdown_pct=0.0),
        })
        result = await trailing_stop_condition(
            data=[{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 113.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["symbol_results"][0]["signal"] == "sell"
        assert result["symbol_results"][0]["hwm_price"] == 120.0

    @pytest.mark.asyncio
    async def test_unregistered_symbol_holds(self):
        # HWM 미등록(이 워크플로우가 매수하지 않은 종목) → hold + 사유
        tracker = MockRiskTracker({})
        result = await trailing_stop_condition(
            data=[{"symbol": "TSLA", "exchange": "NASDAQ", "date": "20260610", "close": 200.0}],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "TSLA", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["result"] is False
        assert result["symbol_results"][0]["reason"] == "HWM 데이터 없음"
        # 미등록 심볼은 update_price 호출 자체가 없어야 함 (price window 오염 방지)
        assert tracker.update_calls == []

    @pytest.mark.asyncio
    async def test_invalid_close_values_skipped(self):
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=100.0, current_price=97.0,
                            position_avg_price=90.0, drawdown_pct=3.0),
        })
        result = await trailing_stop_condition(
            data=[
                {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": "n/a"},
                {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": None},
                {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260610", "close": 0},
            ],
            fields={"trail_percent": 5.0},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        # 유효한 close 가 없으므로 update_price 호출 없음 — 기존 tracker 상태로 평가
        assert tracker.update_calls == []
        assert result["symbol_results"][0]["signal"] == "hold"


class TestRatioModeBackwardCompat:
    """trail_ratio 스케일링 모드 회귀 (trail_percent 미지정/0)"""

    @pytest.mark.asyncio
    async def test_ratio_mode_unchanged(self):
        # 수익 20%, ratio 0.3 → threshold 6%; drawdown 7% > 6% → sell
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=120.0, current_price=111.6,
                            position_avg_price=100.0, drawdown_pct=7.0),
        })
        result = await trailing_stop_condition(
            fields={"trail_ratio": 0.3},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["symbol_results"][0]["signal"] == "sell"
        assert result["symbol_results"][0]["threshold_pct"] == 6.0

    @pytest.mark.asyncio
    async def test_ratio_mode_boundary_excluded(self):
        # 스케일링 모드는 기존 동작(>) 유지: drawdown == threshold 면 hold
        tracker = MockRiskTracker({
            "AAPL": MockHWM(hwm_price=120.0, current_price=112.8,
                            position_avg_price=100.0, drawdown_pct=6.0),
        })
        result = await trailing_stop_condition(
            fields={"trail_ratio": 0.3},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            context=MockContext(tracker),
        )
        assert result["symbol_results"][0]["signal"] == "hold"

    @pytest.mark.asyncio
    async def test_no_risk_tracker_falls_back_to_legacy(self):
        result = await trailing_stop_condition(
            fields={"price_gap_percent": 0.5},
            target_orders=[{"order_id": "1", "symbol": "AAPL", "side": "buy", "price": 100.0}],
            ohlcv_data={"AAPL": {"close": 100.0}},
            context=None,
        )
        assert "modified_orders" in result
        assert result["total_count"] == 1

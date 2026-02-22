"""
DynamicStopLoss (동적 손절) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.dynamic_stop_loss import (
    dynamic_stop_loss_condition,
    _calculate_atr,
    DYNAMIC_STOP_LOSS_SCHEMA,
)


def _make_price_data(symbol, days=30, base=100, volatility=2):
    """시계열 데이터 생성"""
    data = []
    for i in range(days):
        close = base + (i % 3 - 1) * volatility
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close,
            "high": close + volatility,
            "low": close - volatility,
        })
    return data


class TestDynamicStopLossPlugin:
    """DynamicStopLoss 플러그인 테스트"""

    @pytest.fixture
    def price_data(self):
        """시계열 데이터"""
        return _make_price_data("AAPL", days=30, base=150, volatility=3)

    @pytest.fixture
    def positions_normal(self):
        """정상 포지션"""
        return {
            "AAPL": {"current_price": 150, "avg_price": 140, "qty": 10, "market_code": "82"},
        }

    @pytest.fixture
    def positions_stop(self):
        """손절 포지션 (현재가 < 손절가)"""
        return {
            "AAPL": {"current_price": 120, "avg_price": 150, "qty": 10, "market_code": "82"},
        }

    def test_calculate_atr(self):
        """ATR 계산"""
        highs = [102, 104, 103, 105, 106, 104, 107, 105, 108, 106, 109, 107, 110, 108, 111]
        lows = [98, 99, 97, 100, 101, 99, 102, 100, 103, 101, 104, 102, 105, 103, 106]
        closes = [100, 101, 99, 102, 103, 101, 104, 102, 105, 103, 106, 104, 107, 105, 108]
        atr = _calculate_atr(highs, lows, closes, period=10)
        assert atr is not None
        assert atr > 0

    def test_calculate_atr_insufficient(self):
        """데이터 부족"""
        atr = _calculate_atr([100], [99], [100], period=14)
        assert atr is None

    @pytest.mark.asyncio
    async def test_no_trigger(self, price_data, positions_normal):
        """손절 미도달"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_normal,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_stop_triggered(self, price_data, positions_stop):
        """손절 도달"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_stop,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_trailing_mode(self, price_data, positions_normal):
        """트레일링 모드"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_normal,
            fields={"atr_period": 14, "atr_multiplier": 2.0, "trailing": True},
        )
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert sr["reference_price"] >= sr["current_price"] or sr["reference_price"] >= sr["avg_price"]

    @pytest.mark.asyncio
    async def test_no_positions(self):
        """포지션 없음"""
        result = await dynamic_stop_loss_condition(positions={}, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_no_data_fallback(self):
        """시계열 데이터 없이 (fallback ATR)"""
        positions = {"AAPL": {"current_price": 100, "avg_price": 110, "qty": 10, "market_code": "82"}}
        result = await dynamic_stop_loss_condition(
            data=[],
            positions=positions,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert sr["atr"] > 0  # fallback ATR 적용

    @pytest.mark.asyncio
    async def test_symbol_results_detail(self, price_data, positions_normal):
        """결과 상세 포맷"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_normal,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        sr = result["symbol_results"][0]
        assert "atr" in sr
        assert "stop_price" in sr
        assert "stop_distance" in sr
        assert "stop_pct" in sr
        assert "triggered" in sr

    @pytest.mark.asyncio
    async def test_multi_positions(self, price_data):
        """다종목 포지션"""
        data = price_data + _make_price_data("MSFT", 30, 300, 5)
        positions = {
            "AAPL": {"current_price": 150, "avg_price": 140, "qty": 10, "market_code": "82"},
            "MSFT": {"current_price": 250, "avg_price": 300, "qty": 5, "market_code": "82"},
        }
        result = await dynamic_stop_loss_condition(
            data=data,
            positions=positions,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_analysis_output(self, price_data, positions_normal):
        """분석 결과"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_normal,
            fields={"atr_period": 14, "atr_multiplier": 2.0},
        )
        assert result["analysis"]["indicator"] == "DynamicStopLoss"
        assert result["analysis"]["total_positions"] == 1

    @pytest.mark.asyncio
    async def test_exchange_mapping(self, price_data, positions_normal):
        """거래소 코드 매핑"""
        result = await dynamic_stop_loss_condition(
            data=price_data,
            positions=positions_normal,
            fields={},
        )
        sr = result["symbol_results"][0]
        assert sr["exchange"] == "NASDAQ"  # market_code "82" → NASDAQ

    def test_schema(self):
        """스키마 검증"""
        assert DYNAMIC_STOP_LOSS_SCHEMA.id == "DynamicStopLoss"
        assert DYNAMIC_STOP_LOSS_SCHEMA.category == "position"
        assert "atr_period" in DYNAMIC_STOP_LOSS_SCHEMA.fields_schema
        assert "atr_multiplier" in DYNAMIC_STOP_LOSS_SCHEMA.fields_schema
        assert "trailing" in DYNAMIC_STOP_LOSS_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

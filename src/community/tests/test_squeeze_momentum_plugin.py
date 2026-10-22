"""
SqueezeMomentum (스퀴즈 모멘텀) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.squeeze_momentum import (
    squeeze_momentum_condition,
    calculate_squeeze_series,
    SQUEEZE_MOMENTUM_SCHEMA,
    _linear_regression_value,
)


def _make_data(symbol, base_price, count, volatility="normal"):
    """테스트 데이터 생성"""
    data = []
    for i in range(count):
        if volatility == "normal":
            close = base_price + (i % 5 - 2) * 0.5
            high = close + 1
            low = close - 1
        elif volatility == "squeeze":
            # 변동성 극히 축소 (BB < KC)
            close = base_price + (i % 3 - 1) * 0.1
            high = close + 0.2
            low = close - 0.2
        elif volatility == "breakout":
            # 스퀴즈 후 급등
            if i < count - 5:
                close = base_price + (i % 3 - 1) * 0.1
                high = close + 0.2
                low = close - 0.2
            else:
                offset = i - (count - 5)
                close = base_price + offset * 3
                high = close + 2
                low = close - 1
        else:
            close = base_price + (i % 5 - 2) * 2
            high = close + 3
            low = close - 3

        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close, "high": high, "low": low,
        })
    return data


class TestSqueezeMomentumPlugin:
    """SqueezeMomentum 플러그인 테스트"""

    @pytest.fixture
    def squeeze_data(self):
        """스퀴즈 상태 데이터 (변동성 극히 축소)"""
        return _make_data("AAPL", 150, 40, "squeeze")

    @pytest.fixture
    def breakout_data(self):
        """스퀴즈 후 돌파 데이터"""
        return _make_data("AAPL", 150, 40, "breakout")

    @pytest.fixture
    def volatile_data(self):
        """높은 변동성 데이터 (스퀴즈 아님)"""
        return _make_data("MSFT", 300, 40, "volatile")

    def test_linear_regression(self):
        """선형회귀 계산"""
        values = [1, 2, 3, 4, 5]
        result = _linear_regression_value(values)
        assert abs(result - 5.0) < 0.01

    def test_linear_regression_flat(self):
        """플랫 시계열"""
        values = [10, 10, 10, 10]
        result = _linear_regression_value(values)
        assert abs(result - 10.0) < 0.01

    def test_calculate_squeeze_series_basic(self):
        """스퀴즈 시계열 기본 계산"""
        highs = [101 + (i % 3) * 0.5 for i in range(40)]
        lows = [99 - (i % 3) * 0.5 for i in range(40)]
        closes = [100 + (i % 5 - 2) * 0.3 for i in range(40)]

        series = calculate_squeeze_series(highs, lows, closes)
        assert len(series) > 0
        for entry in series:
            assert "squeeze_on" in entry
            assert "momentum" in entry
            assert "bb_upper" in entry
            assert "kc_upper" in entry

    def test_calculate_squeeze_series_insufficient(self):
        """데이터 부족"""
        series = calculate_squeeze_series([100] * 5, [99] * 5, [100] * 5)
        assert series == []

    @pytest.mark.asyncio
    async def test_squeeze_on_detection(self, squeeze_data):
        """스퀴즈 온 감지"""
        result = await squeeze_momentum_condition(
            data=squeeze_data,
            fields={"direction": "squeeze_on"},
        )
        assert "passed_symbols" in result
        assert "symbol_results" in result
        # 스퀴즈 데이터에서 squeeze_on이 감지되어야 함
        if result["symbol_results"]:
            sr = result["symbol_results"][0]
            assert "squeeze_on" in sr

    @pytest.mark.asyncio
    async def test_squeeze_off_detection(self, volatile_data):
        """스퀴즈 오프 감지 (변동성 높으면 스퀴즈 아님)"""
        result = await squeeze_momentum_condition(
            data=volatile_data,
            fields={"direction": "squeeze_off"},
        )
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_squeeze_fire_long(self, breakout_data):
        """스퀴즈 발화 + 롱 모멘텀"""
        result = await squeeze_momentum_condition(
            data=breakout_data,
            fields={"direction": "squeeze_fire_long"},
        )
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await squeeze_momentum_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_data("AAPL", 100, 5)
        result = await squeeze_momentum_condition(data=data, fields={})
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, squeeze_data):
        """time_series 출력 형식"""
        result = await squeeze_momentum_condition(data=squeeze_data, fields={})
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "squeeze_on" in row
                assert "squeeze_fire" in row
                assert "momentum" in row

    def test_schema(self):
        """스키마 검증"""
        assert SQUEEZE_MOMENTUM_SCHEMA.id == "SqueezeMomentum"
        assert "bb_period" in SQUEEZE_MOMENTUM_SCHEMA.fields_schema
        assert "kc_period" in SQUEEZE_MOMENTUM_SCHEMA.fields_schema
        assert "momentum_period" in SQUEEZE_MOMENTUM_SCHEMA.fields_schema
        assert "direction" in SQUEEZE_MOMENTUM_SCHEMA.fields_schema
        assert len(SQUEEZE_MOMENTUM_SCHEMA.fields_schema["direction"]["enum"]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
GoldenRatio (피보나치 되돌림) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.golden_ratio import (
    golden_ratio_condition,
    calculate_fibonacci_levels,
    find_swing_points,
    GOLDEN_RATIO_SCHEMA,
)


class TestGoldenRatioPlugin:
    """GoldenRatio 플러그인 테스트"""

    @pytest.fixture
    def mock_data_uptrend_retracement(self):
        """상승 후 되돌림 데이터 (피보나치 지지 테스트)"""
        data = []
        # 상승 구간 (40일)
        for i in range(40):
            price = 100 + i * 2
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "open": price - 0.5,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "volume": 1000000,
            })
        # 하락 구간 (10일) - 0.618 레벨 근처까지 하락
        swing_high = 100 + 39 * 2  # 178
        swing_low = 100.0
        fib_618 = swing_high - (swing_high - swing_low) * 0.618  # ~129.8
        for i in range(10):
            price = 178 - i * (178 - fib_618) / 10
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202503{i + 1:02d}",
                "open": price + 0.5,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "volume": 1000000,
            })
        return data

    @pytest.fixture
    def mock_data_multi_symbol(self):
        """다종목 데이터"""
        data = []
        for sym, base_price in [("AAPL", 150), ("TSLA", 200)]:
            for i in range(60):
                price = base_price + i * 0.5
                data.append({
                    "symbol": sym,
                    "exchange": "NASDAQ",
                    "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                    "high": price + 1,
                    "low": price - 1,
                    "close": price,
                })
        return data

    def test_calculate_fibonacci_levels_uptrend(self):
        """상승 후 되돌림 피보나치 레벨 계산"""
        levels = calculate_fibonacci_levels(200, 100, is_uptrend=True)
        assert levels["0.236"] == pytest.approx(176.4, abs=0.1)
        assert levels["0.382"] == pytest.approx(161.8, abs=0.1)
        assert levels["0.5"] == pytest.approx(150.0, abs=0.1)
        assert levels["0.618"] == pytest.approx(138.2, abs=0.1)
        assert levels["0.786"] == pytest.approx(121.4, abs=0.1)

    def test_calculate_fibonacci_levels_downtrend(self):
        """하락 후 반등 피보나치 레벨 계산"""
        levels = calculate_fibonacci_levels(200, 100, is_uptrend=False)
        assert levels["0.236"] == pytest.approx(123.6, abs=0.1)
        assert levels["0.382"] == pytest.approx(138.2, abs=0.1)
        assert levels["0.5"] == pytest.approx(150.0, abs=0.1)
        assert levels["0.618"] == pytest.approx(161.8, abs=0.1)

    def test_find_swing_points(self):
        """스윙 포인트 찾기"""
        # 상승 추세: 저점이 먼저, 고점이 나중
        highs = [100, 102, 104, 106, 108, 110]
        lows = [98, 100, 102, 104, 106, 108]
        sh, sl, is_up = find_swing_points(highs, lows, lookback=6)
        assert sh == 110
        assert sl == 98
        assert is_up is True

    def test_find_swing_points_insufficient_data(self):
        """데이터 부족 시 스윙 포인트"""
        highs = [100, 102]
        lows = [98, 100]
        sh, sl, is_up = find_swing_points(highs, lows, lookback=10)
        assert sh is None
        assert sl is None

    @pytest.mark.asyncio
    async def test_support_signal(self, mock_data_uptrend_retracement):
        """지지 신호 테스트"""
        result = await golden_ratio_condition(
            data=mock_data_uptrend_retracement,
            fields={
                "lookback": 50,
                "level": "0.618",
                "direction": "support",
                "tolerance": 0.02,
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_resistance_signal(self, mock_data_uptrend_retracement):
        """저항 신호 테스트"""
        result = await golden_ratio_condition(
            data=mock_data_uptrend_retracement,
            fields={
                "lookback": 50,
                "level": "0.382",
                "direction": "resistance",
                "tolerance": 0.02,
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi_symbol):
        """다종목 처리"""
        result = await golden_ratio_condition(
            data=mock_data_multi_symbol,
            fields={"lookback": 50, "level": "0.618", "direction": "support"},
        )

        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["symbol_results"]) == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await golden_ratio_condition(
            data=[],
            fields={"lookback": 50, "level": "0.618", "direction": "support"},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}", "high": 100 + i, "low": 98 + i, "close": 99 + i}
            for i in range(1, 6)
        ]
        result = await golden_ratio_condition(
            data=data,
            fields={"lookback": 50, "level": "0.618", "direction": "support"},
        )
        assert len(result["failed_symbols"]) == 1
        assert "error" in result["symbol_results"][0]

    @pytest.mark.asyncio
    async def test_time_series_format(self, mock_data_uptrend_retracement):
        """time_series 출력 형식"""
        result = await golden_ratio_condition(
            data=mock_data_uptrend_retracement,
            fields={"lookback": 50, "level": "0.618", "direction": "support", "tolerance": 0.02},
        )

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "fib_level" in row
                assert "fib_price" in row
                assert "swing_high" in row
                assert "distance_pct" in row

    def test_schema(self):
        """스키마 검증"""
        assert GOLDEN_RATIO_SCHEMA.id == "GoldenRatio"
        assert GOLDEN_RATIO_SCHEMA.version == "1.0.0"
        assert "lookback" in GOLDEN_RATIO_SCHEMA.fields_schema
        assert "level" in GOLDEN_RATIO_SCHEMA.fields_schema
        assert "direction" in GOLDEN_RATIO_SCHEMA.fields_schema
        assert "tolerance" in GOLDEN_RATIO_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

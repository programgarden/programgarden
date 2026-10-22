"""
ThreeLineStrike (삼선 타격) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.three_line_strike import (
    three_line_strike_condition,
    detect_bullish_three_line_strike,
    detect_bearish_three_line_strike,
    is_bullish_candle,
    is_bearish_candle,
    body_ratio,
    THREE_LINE_STRIKE_SCHEMA,
)


class TestThreeLineStrikePlugin:
    """ThreeLineStrike 플러그인 테스트"""

    @pytest.fixture
    def bullish_pattern_data(self):
        """Bullish Three Line Strike 패턴 데이터"""
        data = []
        # 앞부분 더미 (6일)
        for i in range(6):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"2025010{i + 1}",
                "open": 100,
                "high": 102,
                "low": 98,
                "close": 101,
                "volume": 1000000,
            })
        # 3연속 음봉
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ", "date": "20250107",
            "open": 100, "high": 101, "low": 96, "close": 97, "volume": 1500000,
        })
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ", "date": "20250108",
            "open": 97, "high": 98, "low": 93, "close": 94, "volume": 1600000,
        })
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ", "date": "20250109",
            "open": 94, "high": 95, "low": 90, "close": 91, "volume": 1700000,
        })
        # 4번째: 대형 양봉 (전체 감싸기)
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ", "date": "20250110",
            "open": 90, "high": 105, "low": 89, "close": 103, "volume": 3000000,
        })
        return data

    @pytest.fixture
    def bearish_pattern_data(self):
        """Bearish Three Line Strike 패턴 데이터"""
        data = []
        # 앞부분 더미 (6일)
        for i in range(6):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"2025010{i + 1}",
                "open": 200,
                "high": 202,
                "low": 198,
                "close": 199,
                "volume": 2000000,
            })
        # 3연속 양봉
        data.append({
            "symbol": "TSLA", "exchange": "NASDAQ", "date": "20250107",
            "open": 200, "high": 206, "low": 199, "close": 205, "volume": 2500000,
        })
        data.append({
            "symbol": "TSLA", "exchange": "NASDAQ", "date": "20250108",
            "open": 205, "high": 212, "low": 204, "close": 210, "volume": 2600000,
        })
        data.append({
            "symbol": "TSLA", "exchange": "NASDAQ", "date": "20250109",
            "open": 210, "high": 218, "low": 209, "close": 215, "volume": 2700000,
        })
        # 4번째: 대형 음봉 (전체 감싸기)
        data.append({
            "symbol": "TSLA", "exchange": "NASDAQ", "date": "20250110",
            "open": 216, "high": 217, "low": 195, "close": 198, "volume": 5000000,
        })
        return data

    @pytest.fixture
    def no_pattern_data(self):
        """패턴 없는 데이터"""
        data = []
        for i in range(10):
            data.append({
                "symbol": "MSFT",
                "exchange": "NASDAQ",
                "date": f"2025011{i}",
                "open": 300 + i,
                "high": 303 + i,
                "low": 297 + i,
                "close": 301 + i,
                "volume": 1000000,
            })
        return data

    @pytest.fixture
    def mock_data_multi_symbol(self, bullish_pattern_data, no_pattern_data):
        """다종목 데이터"""
        return bullish_pattern_data + no_pattern_data

    def test_is_bullish_candle(self):
        """양봉 판별"""
        assert is_bullish_candle(100, 105) is True
        assert is_bullish_candle(105, 100) is False
        assert is_bullish_candle(100, 100) is False

    def test_is_bearish_candle(self):
        """음봉 판별"""
        assert is_bearish_candle(105, 100) is True
        assert is_bearish_candle(100, 105) is False
        assert is_bearish_candle(100, 100) is False

    def test_body_ratio(self):
        """몸통 비율 계산"""
        # 100% 몸통 (시가=저가, 종가=고가)
        assert body_ratio(100, 110, 100, 110) == pytest.approx(1.0)
        # 50% 몸통
        assert body_ratio(103, 110, 100, 108) == pytest.approx(0.5)
        # 0 range
        assert body_ratio(100, 100, 100, 100) == 0.0

    def test_detect_bullish_pattern(self):
        """Bullish 패턴 감지"""
        candles = [
            {"open": 100, "high": 101, "low": 96, "close": 97},
            {"open": 97, "high": 98, "low": 93, "close": 94},
            {"open": 94, "high": 95, "low": 90, "close": 91},
            {"open": 90, "high": 105, "low": 89, "close": 103},
        ]
        result = detect_bullish_three_line_strike(candles, min_body_pct=0.3)
        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_bearish_pattern(self):
        """Bearish 패턴 감지"""
        candles = [
            {"open": 200, "high": 206, "low": 199, "close": 205},
            {"open": 205, "high": 212, "low": 204, "close": 210},
            {"open": 210, "high": 218, "low": 209, "close": 215},
            {"open": 216, "high": 217, "low": 195, "close": 198},
        ]
        result = detect_bearish_three_line_strike(candles, min_body_pct=0.3)
        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_no_pattern(self):
        """패턴 없는 경우"""
        candles = [
            {"open": 100, "high": 102, "low": 98, "close": 101},
            {"open": 101, "high": 103, "low": 99, "close": 102},
            {"open": 102, "high": 104, "low": 100, "close": 103},
            {"open": 103, "high": 105, "low": 101, "close": 104},
        ]
        result = detect_bullish_three_line_strike(candles, min_body_pct=0.3)
        assert result["detected"] is False

    def test_detect_insufficient_candles(self):
        """캔들 부족"""
        candles = [
            {"open": 100, "high": 101, "low": 96, "close": 97},
            {"open": 97, "high": 98, "low": 93, "close": 94},
        ]
        result = detect_bullish_three_line_strike(candles)
        assert result["detected"] is False

    def test_detect_small_body_filtered(self):
        """몸통이 작은 캔들 필터링"""
        candles = [
            {"open": 100, "high": 110, "low": 90, "close": 99.5},  # body ratio = 0.5/20 = 0.025
            {"open": 99.5, "high": 109, "low": 89, "close": 99},
            {"open": 99, "high": 108, "low": 88, "close": 98.5},
            {"open": 88, "high": 115, "low": 87, "close": 110},
        ]
        result = detect_bullish_three_line_strike(candles, min_body_pct=0.3)
        assert result["detected"] is False

    @pytest.mark.asyncio
    async def test_bullish_condition(self, bullish_pattern_data):
        """Bullish 조건 테스트"""
        result = await three_line_strike_condition(
            data=bullish_pattern_data,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_bearish_condition(self, bearish_pattern_data):
        """Bearish 조건 테스트"""
        result = await three_line_strike_condition(
            data=bearish_pattern_data,
            fields={"pattern": "bearish", "min_body_pct": 0.3},
        )

        assert "passed_symbols" in result
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_pattern_condition(self, no_pattern_data):
        """패턴 없는 조건"""
        result = await three_line_strike_condition(
            data=no_pattern_data,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )

        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi_symbol):
        """다종목 처리"""
        result = await three_line_strike_condition(
            data=mock_data_multi_symbol,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )

        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await three_line_strike_condition(
            data=[],
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 (3일)"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}",
             "open": 100, "high": 102, "low": 98, "close": 101}
            for i in range(1, 4)
        ]
        result = await three_line_strike_condition(
            data=data,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, bullish_pattern_data):
        """time_series 출력 형식"""
        result = await three_line_strike_condition(
            data=bullish_pattern_data,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )

        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][-1]
                assert "candle_type" in row
                assert "body_ratio" in row
                assert "pattern_detected" in row
                assert "confidence" in row

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, bullish_pattern_data):
        """symbol_results 형식"""
        result = await three_line_strike_condition(
            data=bullish_pattern_data,
            fields={"pattern": "bullish", "min_body_pct": 0.3},
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if "error" not in sr:
                assert "pattern_detected" in sr
                assert "confidence" in sr
                assert "pattern_type" in sr

    def test_schema(self):
        """스키마 검증"""
        assert THREE_LINE_STRIKE_SCHEMA.id == "ThreeLineStrike"
        assert THREE_LINE_STRIKE_SCHEMA.version == "1.0.0"
        assert "pattern" in THREE_LINE_STRIKE_SCHEMA.fields_schema
        assert "min_body_pct" in THREE_LINE_STRIKE_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

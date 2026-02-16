"""
Engulfing 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.engulfing import (
    engulfing_condition,
    detect_bullish_engulfing,
    detect_bearish_engulfing,
    ENGULFING_SCHEMA,
)


class TestEngulfingPlugin:

    def test_detect_bullish_engulfing(self):
        """Bullish Engulfing 감지"""
        candles = [
            {"open": 105, "high": 106, "low": 99, "close": 100},  # 음봉
            {"open": 99, "high": 108, "low": 98, "close": 107},   # 큰 양봉 감싸기
        ]
        result = detect_bullish_engulfing(candles, 0.5)
        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_bullish_engulfing_not_engulfing(self):
        """감싸지 않는 경우"""
        candles = [
            {"open": 105, "high": 106, "low": 99, "close": 100},
            {"open": 101, "high": 104, "low": 100, "close": 103},  # 감싸지 않음
        ]
        result = detect_bullish_engulfing(candles, 0.5)
        assert result["detected"] is False

    def test_detect_bearish_engulfing(self):
        """Bearish Engulfing 감지"""
        candles = [
            {"open": 100, "high": 106, "low": 99, "close": 105},  # 양봉
            {"open": 106, "high": 107, "low": 98, "close": 99},   # 큰 음봉 감싸기
        ]
        result = detect_bearish_engulfing(candles, 0.5)
        assert result["detected"] is True

    @pytest.mark.asyncio
    async def test_bullish_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 105, "high": 106, "low": 99, "close": 100, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 99, "high": 108, "low": 98, "close": 107, "volume": 2000000},
        ]
        result = await engulfing_condition(data=data, fields={"pattern": "bullish", "min_body_ratio": 0.5})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_bearish_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 100, "high": 106, "low": 99, "close": 105, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 106, "high": 107, "low": 98, "close": 99, "volume": 2000000},
        ]
        result = await engulfing_condition(data=data, fields={"pattern": "bearish", "min_body_ratio": 0.5})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await engulfing_condition(data=[], fields={"pattern": "bullish"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = []
        for i in range(10):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i+1}",
                "open": 100 + i, "high": 106 + i, "low": 95 + i, "close": 103 + i, "volume": 1000000,
            })
        result = await engulfing_condition(data=data, fields={"pattern": "bullish"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][-1]
                assert "pattern_detected" in row
                assert "confidence" in row
                assert "signal" in row

    def test_schema(self):
        assert ENGULFING_SCHEMA.id == "Engulfing"
        assert "pattern" in ENGULFING_SCHEMA.fields_schema
        assert "min_body_ratio" in ENGULFING_SCHEMA.fields_schema

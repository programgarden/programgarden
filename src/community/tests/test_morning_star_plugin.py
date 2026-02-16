"""
MorningEveningStar 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.morning_evening_star import (
    morning_evening_star_condition,
    detect_morning_star,
    detect_evening_star,
    MORNING_EVENING_STAR_SCHEMA,
)


class TestMorningEveningStarPlugin:

    def test_detect_morning_star(self):
        """샛별 감지: 대음봉 + 소형봉 + 대양봉"""
        candles = [
            {"open": 110, "high": 111, "low": 99, "close": 100},   # 대음봉
            {"open": 100, "high": 101, "low": 99, "close": 100.5}, # 소형봉
            {"open": 101, "high": 112, "low": 100, "close": 111},  # 대양봉
        ]
        result = detect_morning_star(candles, 0.3, 0.5)
        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_morning_star_no_small_middle(self):
        """가운데 봉이 크면 감지 안됨"""
        candles = [
            {"open": 110, "high": 111, "low": 99, "close": 100},
            {"open": 100, "high": 108, "low": 97, "close": 107},  # 큰 봉
            {"open": 107, "high": 115, "low": 106, "close": 114},
        ]
        result = detect_morning_star(candles, 0.3, 0.5)
        assert result["detected"] is False

    def test_detect_evening_star(self):
        """석별 감지: 대양봉 + 소형봉 + 대음봉"""
        candles = [
            {"open": 100, "high": 112, "low": 99, "close": 111},   # 대양봉
            {"open": 111, "high": 112, "low": 110, "close": 111.5}, # 소형봉
            {"open": 111, "high": 112, "low": 99, "close": 100},   # 대음봉
        ]
        result = detect_evening_star(candles, 0.3, 0.5)
        assert result["detected"] is True

    def test_detect_evening_star_no_confirmation(self):
        """3번째 봉 회복 부족"""
        candles = [
            {"open": 100, "high": 112, "low": 99, "close": 111},
            {"open": 111, "high": 112, "low": 110, "close": 111.5},
            {"open": 111, "high": 112, "low": 108, "close": 109},  # 회복 부족
        ]
        result = detect_evening_star(candles, 0.3, 0.5)
        # 3번째 음봉 body = 2, 1번째 양봉 body = 11. 2/11 = 0.18 < 0.5
        assert result["detected"] is False

    @pytest.mark.asyncio
    async def test_morning_star_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 110, "high": 111, "low": 99, "close": 100, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 500000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250103",
             "open": 101, "high": 112, "low": 100, "close": 111, "volume": 2000000},
        ]
        result = await morning_evening_star_condition(data=data, fields={"pattern": "morning_star"})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_evening_star_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 100, "high": 112, "low": 99, "close": 111, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 111, "high": 112, "low": 110, "close": 111.5, "volume": 500000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250103",
             "open": 111, "high": 112, "low": 99, "close": 100, "volume": 2000000},
        ]
        result = await morning_evening_star_condition(data=data, fields={"pattern": "evening_star"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await morning_evening_star_condition(data=[], fields={"pattern": "morning_star"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 100, "high": 105, "low": 95, "close": 103, "volume": 1000000},
        ]
        result = await morning_evening_star_condition(
            data=data, fields={"pattern": "morning_star"},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 110, "high": 111, "low": 99, "close": 100, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 500000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250103",
             "open": 101, "high": 112, "low": 100, "close": 111, "volume": 2000000},
        ]
        result = await morning_evening_star_condition(data=data, fields={"pattern": "morning_star"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][-1]
                assert "pattern_detected" in row
                assert "confidence" in row
                assert "signal" in row

    def test_schema(self):
        assert MORNING_EVENING_STAR_SCHEMA.id == "MorningEveningStar"
        assert "pattern" in MORNING_EVENING_STAR_SCHEMA.fields_schema
        assert "star_body_max" in MORNING_EVENING_STAR_SCHEMA.fields_schema
        assert "confirmation_ratio" in MORNING_EVENING_STAR_SCHEMA.fields_schema

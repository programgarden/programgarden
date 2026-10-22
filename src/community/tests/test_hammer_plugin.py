"""
HammerShootingStar 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.hammer_shooting_star import (
    hammer_shooting_star_condition,
    detect_hammer,
    detect_shooting_star,
    HAMMER_SHOOTING_STAR_SCHEMA,
)


class TestHammerShootingStarPlugin:

    def test_detect_hammer(self):
        """망치형 감지: 긴 아래꼬리, 몸통 상단"""
        candle = {"open": 108, "high": 110, "low": 95, "close": 109}
        result = detect_hammer(candle, 2.0, 0.3)
        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_hammer_no_lower_shadow(self):
        """아래꼬리 없는 경우"""
        candle = {"open": 100, "high": 110, "low": 99, "close": 105}
        result = detect_hammer(candle, 2.0, 0.3)
        assert result["detected"] is False

    def test_detect_shooting_star(self):
        """유성형 감지: 긴 위꼬리, 몸통 하단"""
        candle = {"open": 97, "high": 110, "low": 95, "close": 96}
        result = detect_shooting_star(candle, 2.0, 0.3)
        assert result["detected"] is True

    def test_detect_shooting_star_no_upper_shadow(self):
        """위꼬리 없는 경우"""
        candle = {"open": 105, "high": 106, "low": 95, "close": 100}
        result = detect_shooting_star(candle, 2.0, 0.3)
        assert result["detected"] is False

    @pytest.mark.asyncio
    async def test_hammer_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 108, "high": 110, "low": 95, "close": 109, "volume": 1000000},
        ]
        result = await hammer_shooting_star_condition(data=data, fields={"pattern": "hammer"})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_shooting_star_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 97, "high": 110, "low": 95, "close": 96, "volume": 1000000},
        ]
        result = await hammer_shooting_star_condition(data=data, fields={"pattern": "shooting_star"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await hammer_shooting_star_condition(data=[], fields={"pattern": "hammer"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 108, "high": 110, "low": 95, "close": 109, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000000},
        ]
        result = await hammer_shooting_star_condition(data=data, fields={"pattern": "hammer"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "pattern_detected" in row
                assert "confidence" in row
                assert "signal" in row

    def test_schema(self):
        assert HAMMER_SHOOTING_STAR_SCHEMA.id == "HammerShootingStar"
        assert "pattern" in HAMMER_SHOOTING_STAR_SCHEMA.fields_schema
        assert "shadow_ratio" in HAMMER_SHOOTING_STAR_SCHEMA.fields_schema

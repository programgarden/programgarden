"""
Doji 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.doji import (
    doji_condition,
    detect_doji,
    DOJI_SCHEMA,
)


class TestDojiPlugin:

    def test_detect_standard_doji(self):
        """일반 도지 (시가 ≈ 종가, 양 꼬리가 작음)"""
        # range=10, body=0.2 (2%), upper shadow=1.8 (18%<30%), lower shadow=1.0 (10%<30%)
        candle = {"open": 100.0, "high": 102, "low": 99, "close": 100.2}
        result = detect_doji(candle, 0.1)
        assert result["detected"] is True
        assert result["doji_type"] == "standard"

    def test_detect_long_legged_doji(self):
        """장다리 도지"""
        candle = {"open": 100.0, "high": 110, "low": 90, "close": 100.5}
        result = detect_doji(candle, 0.1)
        assert result["detected"] is True
        assert result["doji_type"] == "long_legged"

    def test_detect_dragonfly_doji(self):
        """잠자리 도지 (긴 아래꼬리)"""
        candle = {"open": 109.5, "high": 110, "low": 90, "close": 109.8}
        result = detect_doji(candle, 0.1)
        assert result["detected"] is True
        assert result["doji_type"] == "dragonfly"

    def test_detect_gravestone_doji(self):
        """비석 도지 (긴 위꼬리)"""
        candle = {"open": 90.5, "high": 110, "low": 90, "close": 90.3}
        result = detect_doji(candle, 0.1)
        assert result["detected"] is True
        assert result["doji_type"] == "gravestone"

    def test_not_doji(self):
        """도지가 아닌 경우 (큰 몸통)"""
        candle = {"open": 95, "high": 110, "low": 90, "close": 108}
        result = detect_doji(candle, 0.1)
        assert result["detected"] is False

    @pytest.mark.asyncio
    async def test_standard_doji_condition(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 100, "high": 105, "low": 95, "close": 100.5, "volume": 1000000},
        ]
        result = await doji_condition(data=data, fields={"doji_type": "standard", "body_threshold": 0.1})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_specific_doji_type_filter(self):
        """특정 도지 유형 필터링"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 109.5, "high": 110, "low": 90, "close": 109.8, "volume": 1000000},
        ]
        # dragonfly 필터
        result = await doji_condition(data=data, fields={"doji_type": "dragonfly", "body_threshold": 0.1})
        assert result["result"] is True

        # gravestone 필터 (같은 데이터, 다른 유형)
        result = await doji_condition(data=data, fields={"doji_type": "gravestone", "body_threshold": 0.1})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await doji_condition(data=[], fields={"doji_type": "standard"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 100, "high": 105, "low": 95, "close": 100.5, "volume": 1000000},
        ]
        result = await doji_condition(data=data, fields={"doji_type": "standard"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "pattern_detected" in row
                assert "doji_type" in row
                assert "body_ratio" in row
                assert "confidence" in row

    def test_schema(self):
        assert DOJI_SCHEMA.id == "Doji"
        assert "doji_type" in DOJI_SCHEMA.fields_schema
        assert "body_threshold" in DOJI_SCHEMA.fields_schema

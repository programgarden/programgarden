"""
HeikinAshi 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.heikin_ashi import (
    heikin_ashi_condition,
    calculate_heikin_ashi,
    HEIKIN_ASHI_SCHEMA,
)


def make_data(symbol, exchange, days, start_price, daily_change):
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.998, 2),
            "high": round(price * 1.015, 2),
            "low": round(price * 0.985, 2),
            "close": round(price, 2),
            "volume": 1000000,
        })
    return data


class TestHeikinAshiSchema:
    def test_schema_id(self):
        assert HEIKIN_ASHI_SCHEMA.id == "HeikinAshi"

    def test_schema_output_fields(self):
        assert "ha_open" in HEIKIN_ASHI_SCHEMA.output_fields
        assert "ha_close" in HEIKIN_ASHI_SCHEMA.output_fields
        assert "consecutive_bullish" in HEIKIN_ASHI_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in HEIKIN_ASHI_SCHEMA.locales

    def test_schema_tags(self):
        assert "heikin-ashi" in HEIKIN_ASHI_SCHEMA.tags


class TestCalculateHeikinAshi:
    def test_basic(self):
        opens = [100.0, 101.0, 102.0, 103.0, 104.0]
        highs = [105.0, 106.0, 107.0, 108.0, 109.0]
        lows = [95.0, 96.0, 97.0, 98.0, 99.0]
        closes = [101.0, 102.0, 103.0, 104.0, 105.0]
        result = calculate_heikin_ashi(opens, highs, lows, closes)
        assert len(result) == 5
        for r in result:
            assert "ha_open" in r and "ha_close" in r

    def test_uptrend_consecutive(self):
        n = 10
        opens = [float(100 + i) for i in range(n)]
        highs = [float(105 + i) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        closes = [float(104 + i) for i in range(n)]
        result = calculate_heikin_ashi(opens, highs, lows, closes)
        assert result[-1]["consecutive_bullish"] > 0

    def test_empty(self):
        assert calculate_heikin_ashi([], [], [], []) == []

    def test_ha_close_formula(self):
        """HA_Close = (O+H+L+C) / 4"""
        opens = [100.0]
        highs = [110.0]
        lows = [90.0]
        closes = [105.0]
        result = calculate_heikin_ashi(opens, highs, lows, closes)
        expected_close = (100 + 110 + 90 + 105) / 4
        assert abs(result[0]["ha_close"] - expected_close) < 0.01

    def test_ha_high_is_max(self):
        opens = [100.0, 102.0]
        highs = [110.0, 112.0]
        lows = [90.0, 92.0]
        closes = [105.0, 108.0]
        result = calculate_heikin_ashi(opens, highs, lows, closes)
        for r in result:
            assert r["ha_high"] >= r["ha_open"]
            assert r["ha_high"] >= r["ha_close"]

    def test_ha_low_is_min(self):
        opens = [100.0, 102.0]
        highs = [110.0, 112.0]
        lows = [90.0, 92.0]
        closes = [105.0, 108.0]
        result = calculate_heikin_ashi(opens, highs, lows, closes)
        for r in result:
            assert r["ha_low"] <= r["ha_open"]
            assert r["ha_low"] <= r["ha_close"]


class TestHeikinAshiCondition:
    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await heikin_ashi_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_bullish_signal(self):
        data = make_data("AAPL", "NASDAQ", 10, 100, 0.02)
        result = await heikin_ashi_condition(
            data, {"signal_type": "bullish", "consecutive_count": 2}, None, None
        )
        assert "passed_symbols" in result
        sr = result["symbol_results"][0]
        assert "ha_open" in sr and "ha_close" in sr

    @pytest.mark.asyncio
    async def test_bearish_signal(self):
        data = make_data("AAPL", "NASDAQ", 10, 200, -0.02)
        result = await heikin_ashi_condition(
            data, {"signal_type": "bearish", "consecutive_count": 2}, None, None
        )
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 10, 100, 0.02) + \
               make_data("TSLA", "NASDAQ", 10, 200, -0.02)
        result = await heikin_ashi_condition(data, {}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_time_series(self):
        data = make_data("AAPL", "NASDAQ", 10, 100, 0.02)
        result = await heikin_ashi_condition(data, {}, None, None)
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "ha_open" in ts[0]

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", 10, 100, 0.01)
        result = await heikin_ashi_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

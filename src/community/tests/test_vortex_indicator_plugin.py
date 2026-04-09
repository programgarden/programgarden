"""
VortexIndicator 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.vortex_indicator import (
    vortex_indicator_condition,
    calculate_vortex,
    VORTEX_INDICATOR_SCHEMA,
)


def make_data(symbol, exchange, days, start_price, daily_change):
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.015, 2),
            "low": round(price * 0.985, 2),
            "close": round(price, 2),
            "volume": 1000000,
        })
    return data


class TestVortexSchema:
    def test_schema_id(self):
        assert VORTEX_INDICATOR_SCHEMA.id == "VortexIndicator"

    def test_schema_output_fields(self):
        assert "plus_vi" in VORTEX_INDICATOR_SCHEMA.output_fields
        assert "minus_vi" in VORTEX_INDICATOR_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in VORTEX_INDICATOR_SCHEMA.locales


class TestCalculateVortex:
    def test_basic(self):
        n = 20
        highs = [float(100 + i) for i in range(n)]
        lows = [float(95 + i) for i in range(n)]
        closes = [float(98 + i) for i in range(n)]
        result = calculate_vortex(highs, lows, closes, 14)
        assert len(result) == n
        valid = [r for r in result if r["plus_vi"] is not None]
        assert len(valid) > 0

    def test_uptrend_plus_vi_higher(self):
        n = 20
        highs = [float(100 + i * 2) for i in range(n)]
        lows = [float(95 + i * 2) for i in range(n)]
        closes = [float(99 + i * 2) for i in range(n)]
        result = calculate_vortex(highs, lows, closes, 14)
        valid = [r for r in result if r["plus_vi"] is not None]
        if valid:
            assert valid[-1]["plus_vi"] > valid[-1]["minus_vi"]

    def test_empty(self):
        assert calculate_vortex([], [], [], 14) == []

    def test_short_data(self):
        result = calculate_vortex([100], [95], [98], 14)
        assert all(r["plus_vi"] is None for r in result)


class TestVortexCondition:
    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await vortex_indicator_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_bullish_trend(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.02)
        result = await vortex_indicator_condition(
            data, {"signal_type": "bullish_trend"}, None, None
        )
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert "plus_vi" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01) + \
               make_data("TSLA", "NASDAQ", 20, 200, -0.01)
        result = await vortex_indicator_condition(data, {}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_time_series(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await vortex_indicator_condition(data, {}, None, None)
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "plus_vi" in ts[0]

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await vortex_indicator_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_analysis_metadata(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await vortex_indicator_condition(data, {"period": 10}, None, None)
        assert result["analysis"]["period"] == 10

"""
Supertrend 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.supertrend import (
    supertrend_condition,
    calculate_supertrend,
    SUPERTREND_SCHEMA,
)


def make_data(symbol, exchange, days, start_price, daily_change):
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2), "high": round(price * 1.015, 2),
            "low": round(price * 0.985, 2), "close": round(price, 2), "volume": 1000000,
        })
    return data


class TestSupertrendPlugin:

    def test_calculate_supertrend_basic(self):
        highs = [float(100 + i) for i in range(20)]
        lows = [float(95 + i) for i in range(20)]
        closes = [float(98 + i) for i in range(20)]
        result = calculate_supertrend(highs, lows, closes, 10, 3.0)
        assert len(result) == 20
        for entry in result:
            assert "supertrend" in entry
            assert "trend" in entry
            assert "upper_band" in entry
            assert "lower_band" in entry

    def test_uptrend_detection(self):
        highs = [float(100 + i * 2) for i in range(30)]
        lows = [float(95 + i * 2) for i in range(30)]
        closes = [float(98 + i * 2) for i in range(30)]
        result = calculate_supertrend(highs, lows, closes, 10, 3.0)
        assert result[-1]["trend"] == "up"

    @pytest.mark.asyncio
    async def test_bullish_signal(self):
        data = make_data("AAPL", "NASDAQ", 15, 200, -0.02)
        data += make_data("AAPL", "NASDAQ", 15, data[-1]["close"], 0.03)
        result = await supertrend_condition(data=data, fields={"signal_type": "bullish"})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_bearish_signal(self):
        data = make_data("AAPL", "NASDAQ", 15, 100, 0.02)
        data += make_data("AAPL", "NASDAQ", 15, data[-1]["close"], -0.03)
        result = await supertrend_condition(data=data, fields={"signal_type": "bearish"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_uptrend_condition(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.02)
        result = await supertrend_condition(data=data, fields={"signal_type": "uptrend"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await supertrend_condition(data=[], fields={"signal_type": "bullish"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01)
        result = await supertrend_condition(data=data, fields={"signal_type": "uptrend"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][-1]
                assert "supertrend" in row
                assert "trend" in row
                assert "signal" in row

    def test_schema(self):
        assert SUPERTREND_SCHEMA.id == "Supertrend"
        assert "period" in SUPERTREND_SCHEMA.fields_schema
        assert "multiplier" in SUPERTREND_SCHEMA.fields_schema
        assert "signal_type" in SUPERTREND_SCHEMA.fields_schema

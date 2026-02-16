"""
Keltner Channel 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.keltner_channel import (
    keltner_channel_condition,
    calculate_keltner,
    KELTNER_CHANNEL_SCHEMA,
)


def make_data(symbol, exchange, days, start_price, daily_change):
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2), "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2), "close": round(price, 2), "volume": 1000000,
        })
    return data


class TestKeltnerChannelPlugin:

    def test_calculate_keltner_basic(self):
        highs = [float(100 + i * 0.5) for i in range(30)]
        lows = [float(95 + i * 0.5) for i in range(30)]
        closes = [float(98 + i * 0.5) for i in range(30)]
        result = calculate_keltner(highs, lows, closes, 20, 10, 1.5)
        assert len(result) > 0
        for entry in result:
            assert "middle" in entry
            assert "upper" in entry
            assert "lower" in entry
            assert entry["upper"] > entry["middle"] > entry["lower"]

    @pytest.mark.asyncio
    async def test_above_upper(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.03)
        result = await keltner_channel_condition(data=data, fields={"direction": "above_upper"})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_below_lower(self):
        data = make_data("AAPL", "NASDAQ", 30, 200, -0.03)
        result = await keltner_channel_condition(data=data, fields={"direction": "below_lower"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_squeeze(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.001)
        result = await keltner_channel_condition(data=data, fields={"direction": "squeeze"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await keltner_channel_condition(data=[], fields={"direction": "above_upper"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01)
        result = await keltner_channel_condition(data=data, fields={"direction": "above_upper"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "middle" in row
                assert "upper" in row
                assert "lower" in row
                assert "signal" in row

    def test_schema(self):
        assert KELTNER_CHANNEL_SCHEMA.id == "KeltnerChannel"
        assert "ema_period" in KELTNER_CHANNEL_SCHEMA.fields_schema
        assert "atr_period" in KELTNER_CHANNEL_SCHEMA.fields_schema

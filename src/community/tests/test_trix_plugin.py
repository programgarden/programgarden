"""
TRIX 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.trix import (
    trix_condition,
    calculate_trix,
    calculate_trix_series,
    TRIX_SCHEMA,
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


class TestTRIXPlugin:

    def test_calculate_trix_basic(self):
        closes = [float(100 + i * 0.5) for i in range(60)]
        trix = calculate_trix(closes, 15)
        assert trix is not None

    def test_calculate_trix_insufficient(self):
        closes = [100.0, 101.0, 102.0]
        trix = calculate_trix(closes, 15)
        assert trix is None

    def test_calculate_trix_series(self):
        closes = [float(100 + i * 0.5) for i in range(60)]
        series = calculate_trix_series(closes, 15, 9)
        assert len(series) > 0
        for entry in series:
            assert "trix" in entry
            assert "signal_line" in entry
            assert "histogram" in entry

    @pytest.mark.asyncio
    async def test_bullish_cross(self):
        data = make_data("AAPL", "NASDAQ", 60, 100, 0.005)
        result = await trix_condition(data=data, fields={"period": 15, "signal_period": 9, "signal_type": "bullish_cross"})
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_above_zero(self):
        data = make_data("AAPL", "NASDAQ", 60, 100, 0.01)
        result = await trix_condition(data=data, fields={"signal_type": "above_zero"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_below_zero(self):
        data = make_data("AAPL", "NASDAQ", 60, 200, -0.01)
        result = await trix_condition(data=data, fields={"signal_type": "below_zero"})
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await trix_condition(data=[], fields={"signal_type": "above_zero"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = make_data("AAPL", "NASDAQ", 60, 100, 0.005)
        result = await trix_condition(data=data, fields={"signal_type": "above_zero"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][-1]
                assert "trix" in row
                assert "signal" in row

    def test_schema(self):
        assert TRIX_SCHEMA.id == "TRIX"
        assert "period" in TRIX_SCHEMA.fields_schema
        assert "signal_period" in TRIX_SCHEMA.fields_schema
        assert "signal_type" in TRIX_SCHEMA.fields_schema

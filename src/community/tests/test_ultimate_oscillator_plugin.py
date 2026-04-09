"""
UltimateOscillator 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.ultimate_oscillator import (
    ultimate_oscillator_condition,
    calculate_ultimate_oscillator,
    ULTIMATE_OSCILLATOR_SCHEMA,
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


class TestUltimateOscillatorSchema:

    def test_schema_id(self):
        assert ULTIMATE_OSCILLATOR_SCHEMA.id == "UltimateOscillator"

    def test_schema_category(self):
        assert str(ULTIMATE_OSCILLATOR_SCHEMA.category) == "technical"

    def test_schema_output_fields(self):
        assert "uo" in ULTIMATE_OSCILLATOR_SCHEMA.output_fields
        assert "current_price" in ULTIMATE_OSCILLATOR_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in ULTIMATE_OSCILLATOR_SCHEMA.locales

    def test_schema_products(self):
        product_values = [str(p) for p in ULTIMATE_OSCILLATOR_SCHEMA.products]
        assert "overseas_stock" in product_values

    def test_schema_tags(self):
        assert "larry-williams" in ULTIMATE_OSCILLATOR_SCHEMA.tags


class TestCalculateUltimateOscillator:

    def test_basic_calculation(self):
        highs = [float(100 + i) for i in range(35)]
        lows = [float(95 + i) for i in range(35)]
        closes = [float(98 + i) for i in range(35)]
        result = calculate_ultimate_oscillator(highs, lows, closes, 7, 14, 28)
        assert len(result) == 35
        # 첫 번째와 period3까지는 None
        assert result[0] is None
        # 마지막은 값이 있어야 함
        assert result[-1] is not None

    def test_uptrend_high_uo(self):
        n = 40
        highs = [float(100 + i * 2) for i in range(n)]
        lows = [float(95 + i * 2) for i in range(n)]
        closes = [float(99 + i * 2) for i in range(n)]
        result = calculate_ultimate_oscillator(highs, lows, closes, 7, 14, 28)
        valid = [v for v in result if v is not None]
        assert len(valid) > 0
        assert valid[-1] > 50  # 상승 추세에서 UO > 50

    def test_range_0_100(self):
        highs = [float(100 + i * 2) for i in range(40)]
        lows = [float(90 + i * 2) for i in range(40)]
        closes = [float(95 + i * 2) for i in range(40)]
        result = calculate_ultimate_oscillator(highs, lows, closes)
        for v in result:
            if v is not None:
                assert 0 <= v <= 100

    def test_empty_input(self):
        assert calculate_ultimate_oscillator([], [], []) == []

    def test_insufficient_data(self):
        result = calculate_ultimate_oscillator([100], [95], [98])
        assert all(v is None for v in result)

    def test_custom_periods(self):
        n = 30
        highs = [float(100 + i) for i in range(n)]
        lows = [float(95 + i) for i in range(n)]
        closes = [float(98 + i) for i in range(n)]
        result = calculate_ultimate_oscillator(highs, lows, closes, 5, 10, 20)
        assert len(result) == n
        valid = [v for v in result if v is not None]
        assert len(valid) > 0


class TestUltimateOscillatorCondition:

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await ultimate_oscillator_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_oversold_signal(self):
        # 하락 추세 → 낮은 UO
        data = make_data("AAPL", "NASDAQ", 40, 200, -0.02)
        result = await ultimate_oscillator_condition(
            data, {"direction": "below", "oversold": 40.0}, None, None
        )
        assert "passed_symbols" in result
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert "uo" in sr

    @pytest.mark.asyncio
    async def test_overbought_signal(self):
        data = make_data("AAPL", "NASDAQ", 40, 100, 0.02)
        result = await ultimate_oscillator_condition(
            data, {"direction": "above", "overbought": 60.0}, None, None
        )
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 40, 100, 0.01) + \
               make_data("TSLA", "NASDAQ", 40, 200, -0.01)
        result = await ultimate_oscillator_condition(data, {}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_time_series(self):
        data = make_data("AAPL", "NASDAQ", 40, 100, 0.01)
        result = await ultimate_oscillator_condition(data, {}, None, None)
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "uo" in ts[0]

    @pytest.mark.asyncio
    async def test_custom_field_mapping(self):
        data = [{
            "sym": "AAPL", "exch": "NASDAQ",
            "dt": f"2026010{i+1}", "hi": 100 + i, "lo": 95 + i, "cl": 98 + i,
        } for i in range(9)]
        mapping = {
            "symbol_field": "sym", "exchange_field": "exch",
            "date_field": "dt", "high_field": "hi", "low_field": "lo", "close_field": "cl",
        }
        result = await ultimate_oscillator_condition(data, {}, mapping, None)
        assert len(result["symbol_results"]) == 1

    @pytest.mark.asyncio
    async def test_analysis_metadata(self):
        data = make_data("AAPL", "NASDAQ", 40, 100, 0.01)
        result = await ultimate_oscillator_condition(
            data, {"period1": 5, "period2": 10, "period3": 20}, None, None
        )
        assert result["analysis"]["period1"] == 5
        assert result["analysis"]["indicator"] == "UltimateOscillator"

    @pytest.mark.asyncio
    async def test_no_data_for_symbol(self):
        data = make_data("AAPL", "NASDAQ", 40, 100, 0.01)
        result = await ultimate_oscillator_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

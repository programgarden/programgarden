"""
Aroon 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.aroon import (
    aroon_condition,
    calculate_aroon,
    AROON_SCHEMA,
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


class TestAroonSchema:

    def test_schema_id(self):
        assert AROON_SCHEMA.id == "Aroon"

    def test_schema_category(self):
        assert str(AROON_SCHEMA.category) == "technical"

    def test_schema_output_fields(self):
        assert "aroon_up" in AROON_SCHEMA.output_fields
        assert "aroon_down" in AROON_SCHEMA.output_fields
        assert "aroon_oscillator" in AROON_SCHEMA.output_fields
        assert "current_price" in AROON_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in AROON_SCHEMA.locales

    def test_schema_products(self):
        product_values = [str(p) for p in AROON_SCHEMA.products]
        assert "overseas_stock" in product_values

    def test_schema_tags(self):
        assert "aroon" in AROON_SCHEMA.tags
        assert "trend" in AROON_SCHEMA.tags


class TestCalculateAroon:

    def test_basic_calculation(self):
        highs = [float(100 + i) for i in range(30)]
        lows = [float(95 + i) for i in range(30)]
        result = calculate_aroon(highs, lows, 25)
        assert len(result) == 30
        for entry in result[25:]:
            assert "aroon_up" in entry
            assert "aroon_down" in entry
            assert "aroon_oscillator" in entry

    def test_uptrend_aroon_up_100(self):
        """상승 추세에서 최고가가 가장 최근 → Aroon Up = 100"""
        n = 30
        highs = [float(100 + i) for i in range(n)]
        lows = [float(95 + i) for i in range(n)]
        result = calculate_aroon(highs, lows, 25)
        assert result[-1]["aroon_up"] == 100.0

    def test_downtrend_aroon_down_100(self):
        """하락 추세에서 최저가가 가장 최근 → Aroon Down = 100"""
        n = 30
        highs = [float(200 - i) for i in range(n)]
        lows = [float(195 - i) for i in range(n)]
        result = calculate_aroon(highs, lows, 25)
        assert result[-1]["aroon_down"] == 100.0

    def test_range_0_100(self):
        highs = [float(100 + i % 10) for i in range(30)]
        lows = [float(95 + i % 10) for i in range(30)]
        result = calculate_aroon(highs, lows, 25)
        for entry in result[25:]:
            assert 0 <= entry["aroon_up"] <= 100
            assert 0 <= entry["aroon_down"] <= 100
            assert -100 <= entry["aroon_oscillator"] <= 100

    def test_oscillator_equals_up_minus_down(self):
        highs = [float(100 + i) for i in range(30)]
        lows = [float(95 + i) for i in range(30)]
        result = calculate_aroon(highs, lows, 25)
        for entry in result[25:]:
            assert abs(entry["aroon_oscillator"] - (entry["aroon_up"] - entry["aroon_down"])) < 0.01

    def test_empty_input(self):
        assert calculate_aroon([], [], 25) == []

    def test_insufficient_data(self):
        result = calculate_aroon([100, 101], [95, 96], 25)
        assert result == []

    def test_custom_period(self):
        highs = [float(100 + i) for i in range(15)]
        lows = [float(95 + i) for i in range(15)]
        result = calculate_aroon(highs, lows, 10)
        assert len(result) == 15


class TestAroonCondition:

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await aroon_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_uptrend_detection(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.02)
        result = await aroon_condition(
            data, {"signal_type": "uptrend", "threshold": 70.0, "period": 25}, None, None
        )
        sr = result["symbol_results"][0]
        assert "aroon_up" in sr
        assert sr["aroon_up"] == 100.0  # 상승 추세

    @pytest.mark.asyncio
    async def test_downtrend_detection(self):
        data = make_data("AAPL", "NASDAQ", 30, 200, -0.02)
        result = await aroon_condition(
            data, {"signal_type": "downtrend", "threshold": 70.0, "period": 25}, None, None
        )
        sr = result["symbol_results"][0]
        assert sr["aroon_down"] == 100.0

    @pytest.mark.asyncio
    async def test_cross_up(self):
        # 하락→상승 전환
        down = [200 * (0.98 ** i) for i in range(15)]
        up = [down[-1] * (1.03 ** i) for i in range(20)]
        all_prices = down + up
        data = []
        for i, p in enumerate(all_prices):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "high": round(p * 1.015, 2), "low": round(p * 0.985, 2),
                "close": round(p, 2), "volume": 1000000,
            })
        result = await aroon_condition(
            data, {"signal_type": "cross_up", "period": 10}, None, None
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01) + \
               make_data("TSLA", "NASDAQ", 30, 200, -0.01)
        result = await aroon_condition(data, {"period": 25}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_time_series(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01)
        result = await aroon_condition(data, {"period": 25}, None, None)
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "aroon_up" in ts[0]
        assert "aroon_down" in ts[0]

    @pytest.mark.asyncio
    async def test_custom_field_mapping(self):
        data = [{
            "sym": "AAPL", "exch": "NASDAQ",
            "dt": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "hi": 100 + i, "lo": 95 + i, "cl": 98 + i,
        } for i in range(30)]
        mapping = {
            "symbol_field": "sym", "exchange_field": "exch",
            "date_field": "dt", "high_field": "hi", "low_field": "lo", "close_field": "cl",
        }
        result = await aroon_condition(data, {"period": 25}, mapping, None)
        assert len(result["symbol_results"]) == 1

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01)
        result = await aroon_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_analysis_metadata(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.01)
        result = await aroon_condition(data, {"period": 10}, None, None)
        assert result["analysis"]["period"] == 10
        assert result["analysis"]["indicator"] == "Aroon"

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        data = make_data("AAPL", "NASDAQ", 30, 100, 0.02)
        result = await aroon_condition(
            data, {"signal_type": "uptrend", "threshold": 90.0, "period": 25}, None, None
        )
        assert result["analysis"]["threshold"] == 90.0

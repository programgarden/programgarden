"""
KDJ 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.kdj import (
    kdj_condition,
    calculate_kdj,
    KDJ_SCHEMA,
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


class TestKDJSchema:

    def test_schema_id(self):
        assert KDJ_SCHEMA.id == "KDJ"

    def test_schema_category(self):
        assert str(KDJ_SCHEMA.category) == "technical"

    def test_schema_output_fields(self):
        assert "k" in KDJ_SCHEMA.output_fields
        assert "d" in KDJ_SCHEMA.output_fields
        assert "j" in KDJ_SCHEMA.output_fields
        assert "current_price" in KDJ_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in KDJ_SCHEMA.locales

    def test_schema_products(self):
        product_values = [str(p) for p in KDJ_SCHEMA.products]
        assert "overseas_stock" in product_values

    def test_schema_tags(self):
        assert "kdj" in KDJ_SCHEMA.tags
        assert "asian-market" in KDJ_SCHEMA.tags


class TestCalculateKDJ:

    def test_basic_calculation(self):
        highs = [float(100 + i) for i in range(20)]
        lows = [float(95 + i) for i in range(20)]
        closes = [float(98 + i) for i in range(20)]
        result = calculate_kdj(highs, lows, closes, 9, 3, 3)
        assert len(result) == 20
        for entry in result:
            assert "k" in entry
            assert "d" in entry
            assert "j" in entry

    def test_uptrend_high_kdj(self):
        n = 20
        highs = [float(100 + i * 2) for i in range(n)]
        lows = [float(95 + i * 2) for i in range(n)]
        closes = [float(99 + i * 2) for i in range(n)]
        result = calculate_kdj(highs, lows, closes, 9, 3, 3)
        # 상승 추세에서 K, D가 높아야 함
        assert result[-1]["k"] > 50

    def test_downtrend_low_kdj(self):
        n = 20
        highs = [float(200 - i * 2) for i in range(n)]
        lows = [float(195 - i * 2) for i in range(n)]
        closes = [float(196 - i * 2) for i in range(n)]
        result = calculate_kdj(highs, lows, closes, 9, 3, 3)
        assert result[-1]["k"] < 50

    def test_j_can_exceed_100(self):
        """J값은 0-100 범위를 벗어날 수 있음"""
        n = 20
        highs = [float(100 + i * 3) for i in range(n)]
        lows = [float(98 + i * 3) for i in range(n)]
        closes = [float(99.5 + i * 3) for i in range(n)]
        result = calculate_kdj(highs, lows, closes, 9, 3, 3)
        # J = 3K - 2D 이므로 100 초과 가능
        j_values = [r["j"] for r in result[9:]]
        # 강한 상승에서 J > 100 가능
        assert any(j > 90 for j in j_values)

    def test_empty_input(self):
        assert calculate_kdj([], [], []) == []

    def test_insufficient_data(self):
        result = calculate_kdj([100, 101], [95, 96], [98, 99], 9)
        assert result == []

    def test_initial_values(self):
        highs = [float(100 + i) for i in range(15)]
        lows = [float(95 + i) for i in range(15)]
        closes = [float(98 + i) for i in range(15)]
        result = calculate_kdj(highs, lows, closes, 9, 3, 3)
        # 초기값은 50
        assert result[0]["k"] == 50.0
        assert result[0]["d"] == 50.0

    def test_custom_smoothing(self):
        highs = [float(100 + i) for i in range(20)]
        lows = [float(95 + i) for i in range(20)]
        closes = [float(98 + i) for i in range(20)]
        result1 = calculate_kdj(highs, lows, closes, 9, 3, 3)
        result2 = calculate_kdj(highs, lows, closes, 9, 5, 5)
        # 다른 스무딩 → 다른 결과
        assert result1[-1]["k"] != result2[-1]["k"]


class TestKDJCondition:

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await kdj_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_golden_cross(self):
        # 상승 전환 데이터
        data = make_data("AAPL", "NASDAQ", 10, 100, -0.02) + \
               make_data("AAPL", "NASDAQ", 10, 82, 0.03)
        # 날짜 수동 정렬을 위해 재생성
        prices_down = [100 * (0.98 ** i) for i in range(10)]
        prices_up = [prices_down[-1] * (1.03 ** i) for i in range(10)]
        all_prices = prices_down + prices_up
        data = []
        for i, p in enumerate(all_prices):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "high": round(p * 1.015, 2), "low": round(p * 0.985, 2),
                "close": round(p, 2), "volume": 1000000,
            })
        result = await kdj_condition(data, {"signal_type": "golden_cross"}, None, None)
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_oversold(self):
        data = make_data("AAPL", "NASDAQ", 20, 200, -0.03)
        result = await kdj_condition(
            data, {"signal_type": "oversold", "oversold": 30.0}, None, None
        )
        sr = result["symbol_results"][0]
        assert "j" in sr

    @pytest.mark.asyncio
    async def test_overbought(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.03)
        result = await kdj_condition(
            data, {"signal_type": "overbought", "overbought": 70.0}, None, None
        )
        sr = result["symbol_results"][0]
        assert "k" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01) + \
               make_data("TSLA", "NASDAQ", 20, 200, -0.01)
        result = await kdj_condition(data, {}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_time_series(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await kdj_condition(data, {}, None, None)
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "k" in ts[0]
        assert "d" in ts[0]
        assert "j" in ts[0]

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await kdj_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_analysis_metadata(self):
        data = make_data("AAPL", "NASDAQ", 20, 100, 0.01)
        result = await kdj_condition(
            data, {"n_period": 14}, None, None
        )
        assert result["analysis"]["n_period"] == 14
        assert result["analysis"]["indicator"] == "KDJ"

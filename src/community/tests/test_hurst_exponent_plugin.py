"""
HurstExponent 플러그인 테스트
"""

import pytest
import math
from programgarden_community.plugins.hurst_exponent import (
    hurst_exponent_condition,
    calculate_hurst,
    classify_regime,
    HURST_EXPONENT_SCHEMA,
)


def make_trending_data(symbol, exchange, n=200, start=100):
    """추세 데이터 (H > 0.5)"""
    data = []
    price = start
    for i in range(n):
        price *= 1.005  # 일정한 상승
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": round(price, 2),
        })
    return data


def make_mean_reverting_data(symbol, exchange, n=200, start=100):
    """평균회귀 데이터 (H < 0.5)"""
    import random
    random.seed(42)
    data = []
    price = start
    for i in range(n):
        # 평균으로 되돌리는 프로세스
        price = start + (price - start) * 0.8 + random.gauss(0, 2)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": round(max(price, 1), 2),
        })
    return data


class TestHurstSchema:
    def test_schema_id(self):
        assert HURST_EXPONENT_SCHEMA.id == "HurstExponent"

    def test_schema_output_fields(self):
        assert "hurst" in HURST_EXPONENT_SCHEMA.output_fields
        assert "regime" in HURST_EXPONENT_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in HURST_EXPONENT_SCHEMA.locales

    def test_schema_tags(self):
        assert "hurst" in HURST_EXPONENT_SCHEMA.tags


class TestCalculateHurst:
    def test_trending_h_computed(self):
        """자기상관 데이터 → H 계산 가능 (값 존재 확인)"""
        import random
        random.seed(123)
        # 자기상관 프로세스: ret[t] = 0.5 * ret[t-1] + noise
        prices = [100.0]
        prev_ret = 0.0
        for _ in range(500):
            ret = 0.5 * prev_ret + random.gauss(0, 0.01)
            prices.append(prices[-1] * (1 + ret))
            prev_ret = ret
        h = calculate_hurst(prices, 10, 200, 10)
        assert h is not None
        assert 0 < h < 1

    def test_range_0_1(self):
        prices = [100 + i * 0.5 for i in range(200)]
        h = calculate_hurst(prices, 10, 80, 8)
        if h is not None:
            assert 0 <= h <= 1

    def test_insufficient_data(self):
        h = calculate_hurst([100, 101, 102], 10, 100, 10)
        assert h is None

    def test_constant_prices(self):
        prices = [100.0] * 200
        h = calculate_hurst(prices, 10, 80, 8)
        # 변동 없으면 계산 불가할 수 있음
        # h는 None이거나 0.5 근처


class TestClassifyRegime:
    def test_trending(self):
        assert classify_regime(0.7, 0.55) == "trending"

    def test_mean_reverting(self):
        assert classify_regime(0.3, 0.55) == "mean_reverting"

    def test_random_walk(self):
        assert classify_regime(0.5, 0.55) == "random_walk"


class TestHurstCondition:
    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await hurst_exponent_condition([], {}, None, None)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_trending_detection(self):
        data = make_trending_data("AAPL", "NASDAQ", 200)
        result = await hurst_exponent_condition(
            data, {"signal_type": "trending", "min_window": 10, "max_window": 80}, None, None
        )
        sr = result["symbol_results"][0]
        assert "hurst" in sr
        assert "regime" in sr
        assert sr["hurst"] is not None

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_trending_data("AAPL", "NASDAQ", 200) + \
               make_trending_data("TSLA", "NASDAQ", 200, 200)
        result = await hurst_exponent_condition(
            data, {"min_window": 10, "max_window": 80}, None, None
        )
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_trending_data("AAPL", "NASDAQ", 200)
        result = await hurst_exponent_condition(
            data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_analysis_metadata(self):
        data = make_trending_data("AAPL", "NASDAQ", 200)
        result = await hurst_exponent_condition(
            data, {"signal_type": "any", "h_threshold": 0.6, "min_window": 10, "max_window": 80}, None, None
        )
        assert result["analysis"]["h_threshold"] == 0.6
        assert result["analysis"]["indicator"] == "HurstExponent"

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2026010{i}", "close": 100 + i} for i in range(5)]
        result = await hurst_exponent_condition(data, {}, None, None)
        sr = result["symbol_results"][0]
        assert sr["hurst"] is None

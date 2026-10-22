"""CalmarRatio 플러그인 테스트"""
import pytest
from programgarden_community.plugins.calmar_ratio import (
    calmar_ratio_condition, calculate_calmar, CALMAR_RATIO_SCHEMA,
)

def make_data(symbol, exchange, days, start_price, daily_change):
    return [{"symbol": symbol, "exchange": exchange, "date": f"2025{(i//28)+1:02d}{(i%28)+1:02d}", "close": round(start_price * ((1 + daily_change) ** i), 2)} for i in range(days)]

class TestCalmarSchema:
    def test_id(self): assert CALMAR_RATIO_SCHEMA.id == "CalmarRatio"
    def test_output_fields(self):
        assert "calmar_ratio" in CALMAR_RATIO_SCHEMA.output_fields
        assert "cagr" in CALMAR_RATIO_SCHEMA.output_fields
        assert "max_drawdown" in CALMAR_RATIO_SCHEMA.output_fields
    def test_locales(self): assert "ko" in CALMAR_RATIO_SCHEMA.locales

class TestCalculateCalmar:
    def test_uptrend(self):
        prices = [100 * (1.003 ** i) for i in range(300)]
        r = calculate_calmar(prices, 252)
        assert r["calmar_ratio"] is not None
        assert r["cagr"] > 0

    def test_downtrend(self):
        prices = [200 * (0.997 ** i) for i in range(300)]
        r = calculate_calmar(prices, 252)
        assert r["calmar_ratio"] is not None
        assert r["cagr"] < 0

    def test_mdd_positive(self):
        import random; random.seed(42)
        prices = [100]
        for _ in range(300):
            prices.append(prices[-1] * (1 + random.gauss(0, 0.02)))
        r = calculate_calmar(prices, 252)
        if r["max_drawdown"] is not None:
            assert r["max_drawdown"] >= 0

    def test_insufficient(self):
        r = calculate_calmar([100, 101], 252)
        assert r["calmar_ratio"] is None

    def test_no_drawdown(self):
        """완벽한 상승 → MDD ≈ 0"""
        prices = [100 * (1.001 ** i) for i in range(300)]
        r = calculate_calmar(prices, 252)
        assert r["max_drawdown"] is not None
        assert r["max_drawdown"] < 0.1

class TestCalmarCondition:
    @pytest.mark.asyncio
    async def test_empty(self):
        r = await calmar_ratio_condition([], {}, None, None)
        assert r["result"] is False

    @pytest.mark.asyncio
    async def test_basic(self):
        data = make_data("AAPL", "NASDAQ", 300, 100, 0.002)
        r = await calmar_ratio_condition(data, {"lookback": 252}, None, None)
        assert len(r["symbol_results"]) == 1
        sr = r["symbol_results"][0]
        assert "calmar_ratio" in sr
        assert "cagr" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 300, 100, 0.002) + make_data("TSLA", "NASDAQ", 300, 200, -0.001)
        r = await calmar_ratio_condition(data, {"lookback": 252}, None, None)
        assert len(r["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_above_threshold(self):
        data = make_data("AAPL", "NASDAQ", 300, 100, 0.003)
        r = await calmar_ratio_condition(data, {"lookback": 252, "threshold": 0.5, "direction": "above"}, None, None)
        assert "passed_symbols" in r

    @pytest.mark.asyncio
    async def test_analysis(self):
        data = make_data("AAPL", "NASDAQ", 300, 100, 0.001)
        r = await calmar_ratio_condition(data, {"lookback": 200}, None, None)
        assert r["analysis"]["lookback"] == 200

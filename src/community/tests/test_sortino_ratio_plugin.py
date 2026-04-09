"""SortinoRatio 플러그인 테스트"""
import pytest
from programgarden_community.plugins.sortino_ratio import (
    sortino_ratio_condition, calculate_sortino, SORTINO_RATIO_SCHEMA,
)

def make_data(symbol, exchange, days, start_price, daily_change):
    return [{"symbol": symbol, "exchange": exchange, "date": f"2026{(i//28)+1:02d}{(i%28)+1:02d}", "close": round(start_price * ((1 + daily_change) ** i), 2)} for i in range(days)]

class TestSortinoSchema:
    def test_id(self): assert SORTINO_RATIO_SCHEMA.id == "SortinoRatio"
    def test_output_fields(self):
        assert "sortino_ratio" in SORTINO_RATIO_SCHEMA.output_fields
        assert "downside_deviation" in SORTINO_RATIO_SCHEMA.output_fields
    def test_locales(self): assert "ko" in SORTINO_RATIO_SCHEMA.locales

class TestCalculateSortino:
    def test_uptrend(self):
        prices = [100 * (1.003 ** i) for i in range(100)]
        r = calculate_sortino(prices, 60)
        assert r["sortino_ratio"] is not None
        assert r["sortino_ratio"] > 0

    def test_downtrend(self):
        prices = [200 * (0.997 ** i) for i in range(100)]
        r = calculate_sortino(prices, 60)
        assert r["sortino_ratio"] is not None
        assert r["sortino_ratio"] < 0

    def test_insufficient(self):
        r = calculate_sortino([100], 60)
        assert r["sortino_ratio"] is None

    def test_downside_deviation_positive(self):
        import random; random.seed(42)
        prices = [100 * (1 + random.gauss(0, 0.02)) for _ in range(100)]
        prices = [max(p, 1) for p in prices]
        r = calculate_sortino(prices, 60)
        if r["downside_deviation"] is not None:
            assert r["downside_deviation"] >= 0

    def test_sortino_ge_sharpe_for_uptrend(self):
        """상승 + 노이즈에서 하방 변동이 적으면 Sortino > Sharpe"""
        import random; random.seed(42)
        prices = [100]
        for _ in range(100):
            prices.append(prices[-1] * (1 + 0.003 + random.gauss(0, 0.01)))
        from programgarden_community.plugins.sharpe_ratio_monitor import calculate_sharpe
        sharpe = calculate_sharpe(prices, 60, 0.0)
        sortino = calculate_sortino(prices, 60, 0.0)
        if sharpe["sharpe_ratio"] and sortino["sortino_ratio"]:
            assert sortino["sortino_ratio"] >= sharpe["sharpe_ratio"]

class TestSortinoCondition:
    @pytest.mark.asyncio
    async def test_empty(self):
        r = await sortino_ratio_condition([], {}, None, None)
        assert r["result"] is False

    @pytest.mark.asyncio
    async def test_basic(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.003)
        r = await sortino_ratio_condition(data, {"lookback": 60}, None, None)
        assert len(r["symbol_results"]) == 1
        assert "sortino_ratio" in r["symbol_results"][0]

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.003) + make_data("TSLA", "NASDAQ", 100, 200, -0.002)
        r = await sortino_ratio_condition(data, {"lookback": 60}, None, None)
        assert len(r["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_analysis(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.001)
        r = await sortino_ratio_condition(data, {"mar": 0.05}, None, None)
        assert r["analysis"]["mar"] == 0.05

"""SharpeRatioMonitor 플러그인 테스트"""
import pytest
from programgarden_community.plugins.sharpe_ratio_monitor import (
    sharpe_ratio_monitor_condition, calculate_sharpe, SHARPE_RATIO_MONITOR_SCHEMA,
)

def make_data(symbol, exchange, days, start_price, daily_change):
    return [{"symbol": symbol, "exchange": exchange, "date": f"2026{(i//28)+1:02d}{(i%28)+1:02d}", "close": round(start_price * ((1 + daily_change) ** i), 2)} for i in range(days)]

class TestSharpeSchema:
    def test_id(self): assert SHARPE_RATIO_MONITOR_SCHEMA.id == "SharpeRatioMonitor"
    def test_output_fields(self):
        assert "sharpe_ratio" in SHARPE_RATIO_MONITOR_SCHEMA.output_fields
        assert "annualized_return" in SHARPE_RATIO_MONITOR_SCHEMA.output_fields
    def test_locales(self): assert "ko" in SHARPE_RATIO_MONITOR_SCHEMA.locales
    def test_tags(self): assert "sharpe" in SHARPE_RATIO_MONITOR_SCHEMA.tags

class TestCalculateSharpe:
    def test_uptrend(self):
        prices = [100 * (1.002 ** i) for i in range(100)]
        r = calculate_sharpe(prices, 60, 0.04)
        assert r["sharpe_ratio"] is not None
        assert r["sharpe_ratio"] > 0

    def test_downtrend(self):
        prices = [200 * (0.998 ** i) for i in range(100)]
        r = calculate_sharpe(prices, 60, 0.04)
        assert r["sharpe_ratio"] is not None
        assert r["sharpe_ratio"] < 0

    def test_insufficient(self):
        r = calculate_sharpe([100, 101], 60)
        assert r["sharpe_ratio"] is None

    def test_volatility_positive(self):
        import random; random.seed(42)
        prices = [100 + random.gauss(0, 5) for _ in range(100)]
        prices = [max(p, 1) for p in prices]
        r = calculate_sharpe(prices, 60)
        if r["annualized_volatility"] is not None:
            assert r["annualized_volatility"] > 0

class TestSharpeCondition:
    @pytest.mark.asyncio
    async def test_empty(self):
        r = await sharpe_ratio_monitor_condition([], {}, None, None)
        assert r["result"] is False

    @pytest.mark.asyncio
    async def test_above_threshold(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.005)
        r = await sharpe_ratio_monitor_condition(data, {"threshold": 0.5, "direction": "above", "lookback": 60}, None, None)
        assert "symbol_results" in r
        sr = r["symbol_results"][0]
        assert "sharpe_ratio" in sr

    @pytest.mark.asyncio
    async def test_below_threshold(self):
        data = make_data("AAPL", "NASDAQ", 100, 200, -0.005)
        r = await sharpe_ratio_monitor_condition(data, {"threshold": 0.0, "direction": "below", "lookback": 60}, None, None)
        assert "symbol_results" in r

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.003) + make_data("TSLA", "NASDAQ", 100, 200, -0.003)
        r = await sharpe_ratio_monitor_condition(data, {"lookback": 60}, None, None)
        assert len(r["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.001)
        r = await sharpe_ratio_monitor_condition(data, {}, None, [{"symbol": "MSFT", "exchange": "NASDAQ"}])
        assert len(r["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_analysis(self):
        data = make_data("AAPL", "NASDAQ", 100, 100, 0.001)
        r = await sharpe_ratio_monitor_condition(data, {"lookback": 30, "risk_free_rate": 0.05}, None, None)
        assert r["analysis"]["lookback"] == 30
        assert r["analysis"]["risk_free_rate"] == 0.05

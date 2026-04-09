"""
RSIDivergence 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.rsi_divergence import (
    rsi_divergence_condition,
    detect_divergence,
    find_local_minima,
    find_local_maxima,
    RSI_DIVERGENCE_SCHEMA,
    _calculate_rsi_series,
)


def make_data(symbol, exchange, prices, start_date="20260101"):
    """테스트 데이터 생성 (close 리스트 → flat 배열)"""
    data = []
    for i, price in enumerate(prices):
        day = int(start_date[6:]) + i
        month = int(start_date[4:6]) + (day - 1) // 28
        day = ((day - 1) % 28) + 1
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"{start_date[:4]}{month:02d}{day:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "close": round(price, 2),
            "volume": 1000000,
        })
    return data


def make_bullish_divergence_prices(n=60):
    """강세 다이버전스 데이터: 가격 LL + RSI HL"""
    prices = []
    # 초기 상승
    for i in range(15):
        prices.append(100 + i * 0.5)
    # 하락 → 저점 1 (깊은 하락)
    for i in range(10):
        prices.append(107.5 - i * 1.5)
    # 반등
    for i in range(10):
        prices.append(92.5 + i * 1.0)
    # 다시 하락 → 저점 2 (더 깊은 하락이지만 RSI는 덜 떨어짐 - 완만한 하락)
    for i in range(10):
        prices.append(102.5 - i * 1.2)
    # 마무리 반등
    for i in range(n - 45):
        prices.append(90.5 + i * 0.3)
    return prices[:n]


def make_bearish_divergence_prices(n=60):
    """약세 다이버전스 데이터: 가격 HH + RSI LH"""
    prices = []
    # 초기 하락
    for i in range(15):
        prices.append(100 - i * 0.5)
    # 상승 → 고점 1
    for i in range(10):
        prices.append(92.5 + i * 1.5)
    # 하락
    for i in range(10):
        prices.append(107.5 - i * 1.0)
    # 다시 상승 → 고점 2 (더 높은 고점이지만 RSI는 덜 오름 - 완만한 상승)
    for i in range(10):
        prices.append(97.5 + i * 1.2)
    # 마무리
    for i in range(n - 45):
        prices.append(109.5 - i * 0.3)
    return prices[:n]


class TestRSIDivergenceSchema:

    def test_schema_id(self):
        assert RSI_DIVERGENCE_SCHEMA.id == "RSIDivergence"

    def test_schema_category(self):
        assert str(RSI_DIVERGENCE_SCHEMA.category) == "technical"

    def test_schema_output_fields(self):
        assert "rsi" in RSI_DIVERGENCE_SCHEMA.output_fields
        assert "divergence" in RSI_DIVERGENCE_SCHEMA.output_fields
        assert "divergence_strength" in RSI_DIVERGENCE_SCHEMA.output_fields
        assert "current_price" in RSI_DIVERGENCE_SCHEMA.output_fields

    def test_schema_locales(self):
        assert "ko" in RSI_DIVERGENCE_SCHEMA.locales

    def test_schema_required_fields(self):
        assert "close" in RSI_DIVERGENCE_SCHEMA.required_fields

    def test_schema_products(self):
        product_values = [str(p) for p in RSI_DIVERGENCE_SCHEMA.products]
        assert "overseas_stock" in product_values

    def test_schema_tags(self):
        assert "divergence" in RSI_DIVERGENCE_SCHEMA.tags
        assert "rsi" in RSI_DIVERGENCE_SCHEMA.tags


class TestHelperFunctions:

    def test_find_local_minima(self):
        values = [5, 3, 1, 3, 5, 4, 2, 4, 6]
        minima = find_local_minima(values, 1)
        assert 2 in minima  # value 1
        assert 6 in minima  # value 2

    def test_find_local_maxima(self):
        values = [1, 3, 5, 3, 1, 2, 6, 2, 0]
        maxima = find_local_maxima(values, 1)
        assert 2 in maxima  # value 5
        assert 6 in maxima  # value 6

    def test_find_local_minima_larger_window(self):
        values = [5, 4, 3, 2, 1, 2, 3, 4, 5]
        minima = find_local_minima(values, 2)
        assert 4 in minima

    def test_rsi_series_length(self):
        prices = [100 + i for i in range(30)]
        rsi = _calculate_rsi_series(prices, 14)
        assert len(rsi) == len(prices)

    def test_rsi_series_insufficient_data(self):
        prices = [100, 101, 102]
        rsi = _calculate_rsi_series(prices, 14)
        assert len(rsi) == len(prices)
        assert all(v == 50.0 for v in rsi)


class TestDetectDivergence:

    def test_no_divergence_flat_data(self):
        prices = [100.0] * 60
        rsi = [50.0] * 60
        result = detect_divergence(prices, rsi, 3, 50, "both")
        assert result["divergence"] == "none"

    def test_insufficient_data(self):
        prices = [100.0] * 5
        rsi = [50.0] * 5
        result = detect_divergence(prices, rsi, 3, 50, "bullish")
        assert result["divergence"] == "none"


class TestRSIDivergenceCondition:

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await rsi_divergence_condition([], {}, None, None)
        assert result["result"] is False
        assert result["passed_symbols"] == []

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        data = make_data("AAPL", "NASDAQ", [100, 101, 102])
        result = await rsi_divergence_condition(data, {"rsi_period": 14}, None, None)
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_basic_structure(self):
        prices = [100 + i * 0.5 for i in range(60)]
        data = make_data("AAPL", "NASDAQ", prices)
        result = await rsi_divergence_condition(
            data, {"rsi_period": 14, "lookback": 50, "pivot_window": 3}, None, None
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_symbol_results_fields(self):
        prices = [100 + i * 0.5 for i in range(60)]
        data = make_data("AAPL", "NASDAQ", prices)
        result = await rsi_divergence_condition(
            data, {"rsi_period": 14}, None, None
        )
        sr = result["symbol_results"][0]
        assert "rsi" in sr
        assert "divergence" in sr
        assert "divergence_strength" in sr
        assert "current_price" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        prices1 = [100 + i for i in range(60)]
        prices2 = [200 - i for i in range(60)]
        data = make_data("AAPL", "NASDAQ", prices1) + make_data("TSLA", "NASDAQ", prices2)
        result = await rsi_divergence_condition(data, {"rsi_period": 14}, None, None)
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_custom_field_mapping(self):
        data = [{
            "sym": "AAPL", "exch": "NASDAQ",
            "dt": f"2026010{i+1}", "price": 100 + i,
        } for i in range(30)]
        mapping = {
            "symbol_field": "sym", "exchange_field": "exch",
            "date_field": "dt", "close_field": "price",
        }
        result = await rsi_divergence_condition(data, {"rsi_period": 14}, mapping, None)
        assert len(result["symbol_results"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_output(self):
        prices = [100 + i * 0.5 for i in range(40)]
        data = make_data("AAPL", "NASDAQ", prices)
        result = await rsi_divergence_condition(
            data, {"rsi_period": 14}, None, None
        )
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "rsi" in ts[0]

    @pytest.mark.asyncio
    async def test_both_divergence_type(self):
        prices = [100 + i * 0.5 for i in range(60)]
        data = make_data("AAPL", "NASDAQ", prices)
        result = await rsi_divergence_condition(
            data, {"divergence_type": "both", "rsi_period": 14}, None, None
        )
        assert result["analysis"]["divergence_type"] == "both"

    @pytest.mark.asyncio
    async def test_no_data_symbol(self):
        data = make_data("AAPL", "NASDAQ", [100 + i for i in range(30)])
        result = await rsi_divergence_condition(
            data, {"rsi_period": 14}, None,
            [{"symbol": "MSFT", "exchange": "NASDAQ"}]
        )
        assert len(result["failed_symbols"]) == 1
        assert result["failed_symbols"][0]["symbol"] == "MSFT"

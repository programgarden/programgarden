"""
Ichimoku Cloud 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.ichimoku_cloud import (
    ichimoku_cloud_condition,
    calculate_ichimoku,
    calculate_ichimoku_series,
    ICHIMOKU_CLOUD_SCHEMA,
)


def make_trending_data(symbol, exchange, days, start_price, daily_change):
    """추세 데이터 생성"""
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "close": round(price, 2),
            "volume": 1000000,
        })
    return data


class TestIchimokuCloudPlugin:

    def test_calculate_ichimoku_basic(self):
        """기본 일목균형표 계산"""
        highs = [float(100 + i) for i in range(52)]
        lows = [float(95 + i) for i in range(52)]
        closes = [float(98 + i) for i in range(52)]

        result = calculate_ichimoku(highs, lows, closes, 9, 26, 52)
        assert result is not None
        assert "tenkan_sen" in result
        assert "kijun_sen" in result
        assert "senkou_span_a" in result
        assert "senkou_span_b" in result
        assert "chikou_span" in result

    def test_calculate_ichimoku_insufficient_data(self):
        """데이터 부족 시 None 반환"""
        result = calculate_ichimoku([100, 101], [95, 96], [98, 99], 9, 26, 52)
        assert result is None

    def test_calculate_ichimoku_series(self):
        """시계열 계산"""
        highs = [float(100 + i * 0.5) for i in range(60)]
        lows = [float(95 + i * 0.5) for i in range(60)]
        closes = [float(98 + i * 0.5) for i in range(60)]

        series = calculate_ichimoku_series(highs, lows, closes, 9, 26, 52)
        assert len(series) > 0
        for entry in series:
            assert "tenkan_sen" in entry
            assert "kijun_sen" in entry

    @pytest.mark.asyncio
    async def test_price_above_cloud(self):
        """가격이 구름대 위 (상승 추세)"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 100, 0.01)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52, "signal_type": "price_above_cloud"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_price_below_cloud(self):
        """가격이 구름대 아래 (하락 추세)"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 200, -0.01)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52, "signal_type": "price_below_cloud"},
        )
        assert "passed_symbols" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_tk_cross_bullish(self):
        """텐칸센이 기준선 상향 돌파"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 100, 0.005)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "tk_cross_bullish"},
        )
        assert "passed_symbols" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_tk_cross_bearish(self):
        """텐칸센이 기준선 하향 돌파"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 200, -0.005)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "tk_cross_bearish"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_cloud_bullish(self):
        """구름대 양전환"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 100, 0.01)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "cloud_bullish"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_cloud_bearish(self):
        """구름대 음전환"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 200, -0.01)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "cloud_bearish"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await ichimoku_cloud_condition(data=[], fields={"signal_type": "price_above_cloud"})
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = make_trending_data("AAPL", "NASDAQ", 10, 100, 0.01)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "price_above_cloud"},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 출력 형식"""
        data = make_trending_data("AAPL", "NASDAQ", 60, 100, 0.005)

        result = await ichimoku_cloud_condition(
            data=data,
            fields={"signal_type": "price_above_cloud"},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "tenkan_sen" in row
                assert "kijun_sen" in row
                assert "senkou_span_a" in row
                assert "senkou_span_b" in row
                assert "signal" in row
                assert "side" in row

    def test_schema(self):
        """스키마 검증"""
        assert ICHIMOKU_CLOUD_SCHEMA.id == "IchimokuCloud"
        assert "tenkan_period" in ICHIMOKU_CLOUD_SCHEMA.fields_schema
        assert "kijun_period" in ICHIMOKU_CLOUD_SCHEMA.fields_schema
        assert "senkou_b_period" in ICHIMOKU_CLOUD_SCHEMA.fields_schema
        assert "signal_type" in ICHIMOKU_CLOUD_SCHEMA.fields_schema

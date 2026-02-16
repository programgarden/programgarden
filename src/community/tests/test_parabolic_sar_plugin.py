"""
Parabolic SAR 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.parabolic_sar import (
    parabolic_sar_condition,
    calculate_parabolic_sar,
    PARABOLIC_SAR_SCHEMA,
)


def make_trending_data(symbol, exchange, days, start_price, daily_change):
    data = []
    price = start_price
    for i in range(days):
        price *= (1 + daily_change)
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.015, 2),
            "low": round(price * 0.985, 2),
            "close": round(price, 2),
            "volume": 1000000,
        })
    return data


class TestParabolicSARPlugin:

    def test_calculate_sar_basic(self):
        """기본 SAR 계산"""
        highs = [float(100 + i) for i in range(20)]
        lows = [float(95 + i) for i in range(20)]
        closes = [float(98 + i) for i in range(20)]

        result = calculate_parabolic_sar(highs, lows, closes)
        assert len(result) == 20
        for entry in result:
            assert "sar" in entry
            assert "trend" in entry
            assert entry["trend"] in ("up", "down")

    def test_calculate_sar_insufficient_data(self):
        """데이터 부족"""
        result = calculate_parabolic_sar([100.0], [95.0], [98.0])
        assert len(result) == 0

    def test_uptrend_sar_below_price(self):
        """상승 추세에서 SAR이 가격 아래"""
        highs = [float(100 + i * 2) for i in range(30)]
        lows = [float(95 + i * 2) for i in range(30)]
        closes = [float(98 + i * 2) for i in range(30)]

        result = calculate_parabolic_sar(highs, lows, closes)
        # 후반부는 상승 추세여야 함
        last = result[-1]
        assert last["trend"] == "up"
        assert last["sar"] < closes[-1]

    @pytest.mark.asyncio
    async def test_bullish_reversal(self):
        """상승 반전 시그널"""
        # 하락 후 상승으로 전환
        data = make_trending_data("AAPL", "NASDAQ", 15, 200, -0.02)
        data += make_trending_data("AAPL", "NASDAQ", 15, data[-1]["close"], 0.03)

        result = await parabolic_sar_condition(
            data=data,
            fields={"signal_type": "bullish_reversal"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_bearish_reversal(self):
        """하락 반전 시그널"""
        data = make_trending_data("AAPL", "NASDAQ", 15, 100, 0.02)
        data += make_trending_data("AAPL", "NASDAQ", 15, data[-1]["close"], -0.03)

        result = await parabolic_sar_condition(
            data=data,
            fields={"signal_type": "bearish_reversal"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_uptrend_signal(self):
        """상승 추세 시그널"""
        data = make_trending_data("AAPL", "NASDAQ", 30, 100, 0.02)

        result = await parabolic_sar_condition(
            data=data,
            fields={"signal_type": "uptrend"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_downtrend_signal(self):
        """하락 추세 시그널"""
        data = make_trending_data("AAPL", "NASDAQ", 30, 200, -0.02)

        result = await parabolic_sar_condition(
            data=data,
            fields={"signal_type": "downtrend"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_custom_af_parameters(self):
        """커스텀 가속인자"""
        data = make_trending_data("AAPL", "NASDAQ", 30, 100, 0.01)

        result = await parabolic_sar_condition(
            data=data,
            fields={"af_start": 0.01, "af_step": 0.01, "af_max": 0.10, "signal_type": "uptrend"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await parabolic_sar_condition(data=[], fields={"signal_type": "uptrend"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 형식"""
        data = make_trending_data("AAPL", "NASDAQ", 20, 100, 0.01)

        result = await parabolic_sar_condition(data=data, fields={"signal_type": "uptrend"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "sar" in row
                assert "trend" in row
                assert "signal" in row

    def test_schema(self):
        """스키마 검증"""
        assert PARABOLIC_SAR_SCHEMA.id == "ParabolicSAR"
        assert "af_start" in PARABOLIC_SAR_SCHEMA.fields_schema
        assert "af_step" in PARABOLIC_SAR_SCHEMA.fields_schema
        assert "af_max" in PARABOLIC_SAR_SCHEMA.fields_schema
        assert "signal_type" in PARABOLIC_SAR_SCHEMA.fields_schema

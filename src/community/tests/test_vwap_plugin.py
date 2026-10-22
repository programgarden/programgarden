"""
VWAP 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.vwap import (
    vwap_condition,
    calculate_vwap,
    calculate_vwap_series,
    VWAP_SCHEMA,
)


def make_data(symbol, exchange, days, base_price, direction="up"):
    data = []
    price = base_price
    for i in range(days):
        if direction == "up":
            price *= 1.005
        else:
            price *= 0.995
        data.append({
            "symbol": symbol, "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "close": round(price, 2),
            "volume": 1000000 + i * 10000,
        })
    return data


class TestVWAPPlugin:

    def test_calculate_vwap_basic(self):
        """기본 VWAP 계산"""
        closes = [100.0, 102.0, 101.0, 103.0]
        volumes = [1000, 2000, 1500, 1800]
        highs = [101.0, 103.0, 102.0, 104.0]
        lows = [99.0, 101.0, 100.0, 102.0]

        vwap = calculate_vwap(closes, volumes, highs, lows)
        assert vwap is not None
        assert vwap > 0

    def test_calculate_vwap_no_hl(self):
        """high/low 없이 close만 사용"""
        closes = [100.0, 102.0, 101.0]
        volumes = [1000, 2000, 1500]

        vwap = calculate_vwap(closes, volumes)
        assert vwap is not None

    def test_calculate_vwap_zero_volume(self):
        """거래량 0인 경우"""
        vwap = calculate_vwap([100.0], [0.0])
        assert vwap is None

    def test_calculate_vwap_series(self):
        """VWAP 시계열"""
        closes = [100.0, 102.0, 101.0, 103.0, 104.0]
        volumes = [1000, 2000, 1500, 1800, 2200]

        series = calculate_vwap_series(closes, volumes)
        assert len(series) == 5
        for entry in series:
            assert "vwap" in entry
            assert "upper_band" in entry
            assert "lower_band" in entry

    def test_calculate_vwap_series_with_bands(self):
        """밴드 포함 VWAP 시계열"""
        closes = [100.0, 102.0, 101.0, 103.0, 104.0]
        volumes = [1000, 2000, 1500, 1800, 2200]

        series = calculate_vwap_series(closes, volumes, band_multiplier=2.0)
        assert len(series) == 5
        # 두 번째부터 밴드 있음
        assert series[-1]["upper_band"] is not None
        assert series[-1]["lower_band"] is not None

    @pytest.mark.asyncio
    async def test_above_condition(self):
        """가격이 VWAP 위"""
        data = make_data("AAPL", "NASDAQ", 30, 100, "up")

        result = await vwap_condition(
            data=data,
            fields={"direction": "above", "band_multiplier": 0},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_below_condition(self):
        """가격이 VWAP 아래"""
        data = make_data("AAPL", "NASDAQ", 30, 200, "down")

        result = await vwap_condition(
            data=data,
            fields={"direction": "below"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_with_bands(self):
        """밴드 포함 평가"""
        data = make_data("AAPL", "NASDAQ", 30, 100, "up")

        result = await vwap_condition(
            data=data,
            fields={"direction": "above", "band_multiplier": 2.0},
        )
        for sr in result["symbol_results"]:
            if "error" not in sr:
                assert "vwap" in sr
                assert "upper_band" in sr
                assert "lower_band" in sr

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await vwap_condition(data=[], fields={"direction": "above"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 형식"""
        data = make_data("AAPL", "NASDAQ", 20, 100, "up")

        result = await vwap_condition(data=data, fields={"direction": "above"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "vwap" in row
                assert "signal" in row
                assert "side" in row

    def test_schema(self):
        """스키마 검증"""
        assert VWAP_SCHEMA.id == "VWAP"
        assert "direction" in VWAP_SCHEMA.fields_schema
        assert "band_multiplier" in VWAP_SCHEMA.fields_schema

"""
CMF 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.cmf import (
    cmf_condition,
    calculate_cmf,
    calculate_cmf_series,
    CMF_SCHEMA,
)


class TestCMFPlugin:

    def test_calculate_cmf_accumulation(self):
        """매집 (종가가 고가 근처)"""
        highs = [110.0] * 20
        lows = [90.0] * 20
        closes = [108.0] * 20  # 고가 근처 -> 양의 MFM
        volumes = [1000000.0] * 20

        cmf = calculate_cmf(highs, lows, closes, volumes, 20)
        assert cmf is not None
        assert cmf > 0  # 매집

    def test_calculate_cmf_distribution(self):
        """분산 (종가가 저가 근처)"""
        highs = [110.0] * 20
        lows = [90.0] * 20
        closes = [92.0] * 20  # 저가 근처 -> 음의 MFM
        volumes = [1000000.0] * 20

        cmf = calculate_cmf(highs, lows, closes, volumes, 20)
        assert cmf is not None
        assert cmf < 0  # 분산

    def test_calculate_cmf_insufficient(self):
        cmf = calculate_cmf([100], [90], [95], [1000], 20)
        assert cmf is None

    def test_calculate_cmf_series(self):
        highs = [float(110 + i * 0.1) for i in range(30)]
        lows = [float(90 + i * 0.1) for i in range(30)]
        closes = [float(105 + i * 0.1) for i in range(30)]
        volumes = [1000000.0] * 30

        series = calculate_cmf_series(highs, lows, closes, volumes, 20)
        assert len(series) > 0
        for entry in series:
            assert "cmf" in entry
            assert "mfv" in entry

    @pytest.mark.asyncio
    async def test_accumulation_condition(self):
        data = []
        for i in range(30):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": 110, "low": 90, "close": 108,
                "volume": 1000000,
            })

        result = await cmf_condition(
            data=data,
            fields={"period": 20, "threshold": 0.05, "direction": "accumulation"},
        )
        assert "passed_symbols" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_distribution_condition(self):
        data = []
        for i in range(30):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": 110, "low": 90, "close": 92,
                "volume": 1000000,
            })

        result = await cmf_condition(
            data=data,
            fields={"period": 20, "threshold": 0.05, "direction": "distribution"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await cmf_condition(data=[], fields={"direction": "accumulation"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        data = []
        for i in range(30):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ", "date": f"202501{i+1:02d}",
                "high": 110, "low": 90, "close": 105, "volume": 1000000,
            })
        result = await cmf_condition(data=data, fields={"direction": "accumulation"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "cmf" in row
                assert "mfv" in row
                assert "signal" in row

    def test_schema(self):
        assert CMF_SCHEMA.id == "CMF"
        assert "period" in CMF_SCHEMA.fields_schema
        assert "threshold" in CMF_SCHEMA.fields_schema
        assert "direction" in CMF_SCHEMA.fields_schema

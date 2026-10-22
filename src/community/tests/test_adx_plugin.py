"""
ADX (Average Directional Index) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.adx import (
    adx_condition,
    calculate_adx,
    calculate_adx_series,
    ADX_SCHEMA,
)


class TestADXPlugin:
    """ADX 플러그인 테스트"""

    @pytest.fixture
    def mock_data_strong_uptrend(self):
        """강한 상승 추세 데이터 (ADX 높음, +DI > -DI)"""
        data = []
        price = 100.0
        for i in range(35):
            # 지속적인 상승
            price = price * 1.015
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}" if i < 9 else f"2025{(i//30)+1:02d}{(i%30)+1:02d}",
                "open": price * 0.995,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000000 + i * 10000,
            })
        return data

    @pytest.fixture
    def mock_data_strong_downtrend(self):
        """강한 하락 추세 데이터 (ADX 높음, -DI > +DI)"""
        data = []
        price = 200.0
        for i in range(35):
            # 지속적인 하락
            price = price * 0.985
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "NVDA",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}" if i < 9 else f"2025{(i//30)+1:02d}{(i%30)+1:02d}",
                "open": price * 1.005,
                "high": high,
                "low": low,
                "close": price,
                "volume": 2000000 + i * 10000,
            })
        return data

    @pytest.fixture
    def mock_data_sideways(self):
        """횡보 데이터 (ADX 낮음)"""
        data = []
        price = 100.0
        for i in range(35):
            # 작은 변동
            if i % 2 == 0:
                price = price * 1.002
            else:
                price = price * 0.998
            high = price * 1.005
            low = price * 0.995
            data.append({
                "symbol": "MSFT",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}" if i < 9 else f"2025{(i//30)+1:02d}{(i%30)+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1500000,
            })
        return data

    def test_calculate_adx(self):
        """ADX 계산 테스트"""
        # 상승 추세 데이터
        highs = [100 + i * 2 for i in range(30)]
        lows = [95 + i * 2 for i in range(30)]
        closes = [98 + i * 2 for i in range(30)]

        result = calculate_adx(highs, lows, closes, period=14)

        assert "adx" in result
        assert "plus_di" in result
        assert "minus_di" in result
        assert result["adx"] >= 0
        assert result["plus_di"] >= 0
        assert result["minus_di"] >= 0

    def test_calculate_adx_insufficient_data(self):
        """데이터 부족 시"""
        highs = [100, 101, 102]
        lows = [98, 99, 100]
        closes = [99, 100, 101]

        result = calculate_adx(highs, lows, closes, period=14)

        assert result["adx"] == 0.0
        assert result["plus_di"] == 0.0
        assert result["minus_di"] == 0.0

    def test_calculate_adx_series(self):
        """ADX 시계열 계산 테스트"""
        highs = [100 + i * 1.5 for i in range(35)]
        lows = [95 + i * 1.5 for i in range(35)]
        closes = [98 + i * 1.5 for i in range(35)]

        series = calculate_adx_series(highs, lows, closes, period=14)

        assert len(series) > 0

        for entry in series:
            assert "adx" in entry
            assert "plus_di" in entry
            assert "minus_di" in entry

    @pytest.mark.asyncio
    async def test_strong_uptrend_condition(self, mock_data_strong_uptrend):
        """강한 상승 추세 조건 테스트"""
        result = await adx_condition(
            data=mock_data_strong_uptrend,
            fields={
                "period": 14,
                "threshold": 20,
                "direction": "uptrend",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_strong_downtrend_condition(self, mock_data_strong_downtrend):
        """강한 하락 추세 조건 테스트"""
        result = await adx_condition(
            data=mock_data_strong_downtrend,
            fields={
                "period": 14,
                "threshold": 20,
                "direction": "downtrend",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_sideways_condition(self, mock_data_sideways):
        """횡보 조건 테스트 (강한 추세 없음)"""
        result = await adx_condition(
            data=mock_data_sideways,
            fields={
                "period": 14,
                "threshold": 25,
                "direction": "strong_trend",
            },
        )

        # 횡보 시 ADX가 낮아서 strong_trend 조건 실패 가능
        assert "passed_symbols" in result
        assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_strong_uptrend):
        """symbol_results 형식 확인"""
        result = await adx_condition(
            data=mock_data_strong_uptrend,
            fields={
                "period": 14,
                "threshold": 25,
                "direction": "strong_trend",
            },
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if "error" not in sr:
                assert "adx" in sr
                assert "plus_di" in sr
                assert "minus_di" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_data_strong_uptrend):
        """values의 time_series 형식 확인"""
        result = await adx_condition(
            data=mock_data_strong_uptrend,
            fields={
                "period": 14,
                "threshold": 25,
                "direction": "strong_trend",
            },
        )

        assert len(result["values"]) >= 1

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val

            if val["time_series"]:
                for row in val["time_series"]:
                    assert "adx" in row
                    assert "plus_di" in row
                    assert "minus_di" in row

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await adx_condition(
            data=[],
            fields={
                "period": 14,
                "threshold": 25,
                "direction": "strong_trend",
            },
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 케이스"""
        # 20일 데이터 (최소 28일 필요: period * 2)
        data = []
        for i in range(20):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": 100,
                "high": 105,
                "low": 95,
                "close": 100,
                "volume": 1000000,
            })

        result = await adx_condition(
            data=data,
            fields={
                "period": 14,
                "threshold": 25,
                "direction": "strong_trend",
            },
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        assert len(result["failed_symbols"]) == 1
        assert result["result"] is False

    def test_schema(self):
        """스키마 검증"""
        assert ADX_SCHEMA.id == "ADX"
        assert ADX_SCHEMA.version == "1.0.0"
        assert "period" in ADX_SCHEMA.fields_schema
        assert "threshold" in ADX_SCHEMA.fields_schema
        assert "direction" in ADX_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

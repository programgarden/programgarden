"""
OBV (On-Balance Volume) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.obv import (
    obv_condition,
    calculate_obv,
    calculate_obv_series,
    OBV_SCHEMA,
)


class TestOBVPlugin:
    """OBV 플러그인 테스트"""

    @pytest.fixture
    def mock_data_bullish(self):
        """상승 추세 데이터 (OBV 상승)"""
        data = []
        price = 100.0
        for i in range(25):
            # 지속적인 상승
            price = price * 1.01
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price * 0.99,
                "high": price * 1.01,
                "low": price * 0.98,
                "close": price,
                "volume": 1000000 + i * 50000,
            })
        return data

    @pytest.fixture
    def mock_data_bearish(self):
        """하락 추세 데이터 (OBV 하락)"""
        data = []
        price = 200.0
        for i in range(25):
            # 지속적인 하락
            price = price * 0.99
            data.append({
                "symbol": "NVDA",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price * 1.01,
                "high": price * 1.02,
                "low": price * 0.99,
                "close": price,
                "volume": 2000000 + i * 50000,
            })
        return data

    @pytest.fixture
    def mock_data_mixed(self):
        """혼합 데이터"""
        data = []
        price = 100.0
        for i in range(25):
            if i % 2 == 0:
                price = price * 1.005
            else:
                price = price * 0.995
            data.append({
                "symbol": "MSFT",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1500000,
            })
        return data

    def test_calculate_obv(self):
        """OBV 계산 테스트"""
        closes = [100, 102, 101, 103, 105]
        volumes = [1000, 1200, 800, 1500, 2000]

        obv = calculate_obv(closes, volumes)

        # 102 > 100: +1200
        # 101 < 102: -800
        # 103 > 101: +1500
        # 105 > 103: +2000
        # 총: 1200 - 800 + 1500 + 2000 = 3900
        assert obv == 3900

    def test_calculate_obv_insufficient_data(self):
        """데이터 부족 시"""
        closes = [100]
        volumes = [1000]

        obv = calculate_obv(closes, volumes)
        assert obv == 0.0

    def test_calculate_obv_series(self):
        """OBV 시계열 계산 테스트"""
        closes = [100 + i for i in range(25)]
        volumes = [1000000] * 25

        series = calculate_obv_series(closes, volumes, ma_period=10)

        assert len(series) == 25

        for entry in series:
            assert "obv" in entry
            assert "obv_ma" in entry

    @pytest.mark.asyncio
    async def test_bullish_condition(self, mock_data_bullish):
        """상승 추세 조건 테스트"""
        result = await obv_condition(
            data=mock_data_bullish,
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

        # 상승 추세에서 bullish 조건 통과해야 함
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "AAPL" in passed_syms

    @pytest.mark.asyncio
    async def test_bearish_condition(self, mock_data_bearish):
        """하락 추세 조건 테스트"""
        result = await obv_condition(
            data=mock_data_bearish,
            fields={
                "ma_period": 10,
                "direction": "bearish",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

        # 하락 추세에서 bearish 조건 통과해야 함
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "NVDA" in passed_syms

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_bullish):
        """symbol_results 형식 확인"""
        result = await obv_condition(
            data=mock_data_bullish,
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if "error" not in sr:
                assert "obv" in sr
                assert "obv_ma" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_data_bullish):
        """values의 time_series 형식 확인"""
        result = await obv_condition(
            data=mock_data_bullish,
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
        )

        assert len(result["values"]) >= 1

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val

            if val["time_series"]:
                for row in val["time_series"]:
                    assert "obv" in row
                    assert "obv_ma" in row

    @pytest.mark.asyncio
    async def test_auto_extract_symbols(self, mock_data_bullish):
        """symbols 없이 data에서 자동 추출"""
        result = await obv_condition(
            data=mock_data_bullish,
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
        )

        assert len(result["symbol_results"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await obv_condition(
            data=[],
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 케이스"""
        # 5일 데이터 (최소 20일 필요)
        data = []
        for i in range(5):
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

        result = await obv_condition(
            data=data,
            fields={
                "ma_period": 20,
                "direction": "bullish",
            },
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        assert len(result["failed_symbols"]) == 1
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_data_bullish, mock_data_bearish):
        """다중 종목 테스트"""
        combined_data = mock_data_bullish + mock_data_bearish

        result = await obv_condition(
            data=combined_data,
            fields={
                "ma_period": 10,
                "direction": "bullish",
            },
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "NVDA", "exchange": "NASDAQ"},
            ],
        )

        # AAPL: 상승 -> bullish 통과
        # NVDA: 하락 -> bullish 실패
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        failed_syms = [s["symbol"] for s in result["failed_symbols"]]

        assert "AAPL" in passed_syms
        assert "NVDA" in failed_syms

    def test_schema(self):
        """스키마 검증"""
        assert OBV_SCHEMA.id == "OBV"
        assert OBV_SCHEMA.version == "1.0.0"
        assert "ma_period" in OBV_SCHEMA.fields_schema
        assert "direction" in OBV_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

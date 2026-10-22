"""
MeanReversion (평균 회귀) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.mean_reversion import (
    mean_reversion_condition,
    calculate_sma,
    calculate_std,
    calculate_mean_reversion_series,
    MEAN_REVERSION_SCHEMA,
)


class TestMeanReversionPlugin:
    """MeanReversion 플러그인 테스트"""

    @pytest.fixture
    def mock_data_oversold(self):
        """과매도 데이터 (가격이 MA-2σ 아래)"""
        data = []
        # 안정적인 구간 (30일)
        for i in range(30):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": 100 + (i % 3 - 1) * 0.5,
                "high": 101,
                "low": 99,
            })
        # 급락 (5일)
        for i in range(5):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202502{i + 5:02d}",
                "close": 95 - i * 2,
                "high": 96 - i * 2,
                "low": 94 - i * 2,
            })
        return data

    @pytest.fixture
    def mock_data_overbought(self):
        """과매수 데이터 (가격이 MA+2σ 위)"""
        data = []
        # 안정적인 구간 (30일)
        for i in range(30):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": 200 + (i % 3 - 1) * 0.5,
                "high": 201,
                "low": 199,
            })
        # 급등 (5일)
        for i in range(5):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"202502{i + 5:02d}",
                "close": 205 + i * 3,
                "high": 206 + i * 3,
                "low": 204 + i * 3,
            })
        return data

    @pytest.fixture
    def mock_data_multi_symbol(self):
        """다종목 데이터"""
        data = []
        for sym, base in [("AAPL", 100), ("TSLA", 200)]:
            for i in range(30):
                data.append({
                    "symbol": sym,
                    "exchange": "NASDAQ",
                    "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                    "close": base + (i % 3 - 1),
                })
        return data

    def test_calculate_sma(self):
        """단순 이동평균 계산"""
        values = [10, 20, 30, 40, 50]
        assert calculate_sma(values, 5) == pytest.approx(30.0)
        assert calculate_sma(values, 3) == pytest.approx(40.0)

    def test_calculate_sma_insufficient(self):
        """데이터 부족 시 SMA"""
        values = [10, 20]
        assert calculate_sma(values, 5) == pytest.approx(15.0)

    def test_calculate_std(self):
        """표준편차 계산"""
        values = [10, 10, 10, 10, 10]
        assert calculate_std(values, 5) == pytest.approx(0.0)

        values2 = [10, 20, 30, 40, 50]
        std = calculate_std(values2, 5)
        assert std > 0

    def test_calculate_mean_reversion_series(self):
        """평균 회귀 시계열 계산"""
        closes = list(range(100, 130))
        series = calculate_mean_reversion_series(closes, ma_period=10, deviation=2.0)

        assert len(series) > 0
        for entry in series:
            assert "ma" in entry
            assert "std" in entry
            assert "upper" in entry
            assert "lower" in entry
            assert "deviation_pct" in entry
            assert entry["upper"] >= entry["ma"]
            assert entry["lower"] <= entry["ma"]

    def test_calculate_mean_reversion_series_insufficient(self):
        """데이터 부족 시 빈 시계열"""
        closes = [100, 101, 102]
        series = calculate_mean_reversion_series(closes, ma_period=10)
        assert series == []

    @pytest.mark.asyncio
    async def test_oversold_condition(self, mock_data_oversold):
        """과매도 조건 테스트"""
        result = await mean_reversion_condition(
            data=mock_data_oversold,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert result["result"] is True  # 급락으로 과매도

    @pytest.mark.asyncio
    async def test_overbought_condition(self, mock_data_overbought):
        """과매수 조건 테스트"""
        result = await mean_reversion_condition(
            data=mock_data_overbought,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "overbought"},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert result["result"] is True  # 급등으로 과매수

    @pytest.mark.asyncio
    async def test_normal_condition_fails(self, mock_data_multi_symbol):
        """정상 가격에서 과매도/과매수 실패"""
        result = await mean_reversion_condition(
            data=mock_data_multi_symbol,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )

        assert len(result["failed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi_symbol):
        """다종목 처리"""
        result = await mean_reversion_condition(
            data=mock_data_multi_symbol,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )

        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await mean_reversion_condition(
            data=[],
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}", "close": 100 + i}
            for i in range(1, 6)
        ]
        result = await mean_reversion_condition(
            data=data,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, mock_data_oversold):
        """time_series 출력 형식"""
        result = await mean_reversion_condition(
            data=mock_data_oversold,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )

        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "ma" in row
                assert "upper" in row
                assert "lower" in row
                assert "deviation_pct" in row

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_oversold):
        """symbol_results 형식 확인"""
        result = await mean_reversion_condition(
            data=mock_data_oversold,
            fields={"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if "error" not in sr:
                assert "ma" in sr
                assert "deviation_pct" in sr
                assert "current_price" in sr

    def test_schema(self):
        """스키마 검증"""
        assert MEAN_REVERSION_SCHEMA.id == "MeanReversion"
        assert MEAN_REVERSION_SCHEMA.version == "1.0.0"
        assert "ma_period" in MEAN_REVERSION_SCHEMA.fields_schema
        assert "deviation" in MEAN_REVERSION_SCHEMA.fields_schema
        assert "direction" in MEAN_REVERSION_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

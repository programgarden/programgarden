"""
ZScore (Z-Score) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.z_score import (
    z_score_condition,
    calculate_z_score,
    calculate_z_score_series,
    Z_SCORE_SCHEMA,
)


class TestZScorePlugin:
    """ZScore 플러그인 테스트"""

    @pytest.fixture
    def mock_data_oversold(self):
        """과매도 데이터 (Z < -2)"""
        data = []
        for i in range(30):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": 100 + (i % 3 - 1) * 0.5,
                "high": 101, "low": 99,
            })
        # 급락 (5일)
        for i in range(5):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202502{i + 5:02d}",
                "close": 93 - i * 2,
                "high": 94 - i * 2, "low": 92 - i * 2,
            })
        return data

    @pytest.fixture
    def mock_data_overbought(self):
        """과매수 데이터 (Z > +2)"""
        data = []
        for i in range(30):
            data.append({
                "symbol": "TSLA", "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": 200 + (i % 3 - 1) * 0.5,
                "high": 201, "low": 199,
            })
        for i in range(5):
            data.append({
                "symbol": "TSLA", "exchange": "NASDAQ",
                "date": f"202502{i + 5:02d}",
                "close": 208 + i * 3,
                "high": 209 + i * 3, "low": 207 + i * 3,
            })
        return data

    @pytest.fixture
    def mock_data_multi(self):
        """다종목 데이터"""
        data = []
        for sym, base in [("AAPL", 100), ("TSLA", 200)]:
            for i in range(30):
                data.append({
                    "symbol": sym, "exchange": "NASDAQ",
                    "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                    "close": base + (i % 3 - 1),
                })
        return data

    def test_calculate_z_score_basic(self):
        """기본 Z-Score 계산"""
        prices = [100] * 19 + [110]
        z = calculate_z_score(prices, lookback=20)
        assert z is not None
        assert z > 0  # 평균 위

    def test_calculate_z_score_zero_std(self):
        """표준편차 0일 때"""
        prices = [100] * 20
        z = calculate_z_score(prices, lookback=20)
        assert z == 0.0

    def test_calculate_z_score_insufficient(self):
        """데이터 부족"""
        z = calculate_z_score([100, 101], lookback=20)
        assert z is None

    def test_calculate_z_score_series(self):
        """Z-Score 시계열"""
        prices = list(range(100, 130))
        series = calculate_z_score_series(prices, lookback=10)
        assert len(series) > 0
        for entry in series:
            assert "z_score" in entry
            assert "mean" in entry
            assert "std" in entry

    def test_calculate_z_score_series_insufficient(self):
        """데이터 부족 시 빈 시계열"""
        series = calculate_z_score_series([100, 101], lookback=20)
        assert series == []

    @pytest.mark.asyncio
    async def test_oversold_condition(self, mock_data_oversold):
        """과매도 (Z < -entry) 조건"""
        result = await z_score_condition(
            data=mock_data_oversold,
            fields={"lookback": 20, "entry_threshold": 2.0, "direction": "below"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_overbought_condition(self, mock_data_overbought):
        """과매수 (Z > +entry) 조건"""
        result = await z_score_condition(
            data=mock_data_overbought,
            fields={"lookback": 20, "entry_threshold": 2.0, "direction": "above"},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_normal_fails(self, mock_data_multi):
        """정상 가격에서 조건 미충족"""
        result = await z_score_condition(
            data=mock_data_multi,
            fields={"lookback": 20, "entry_threshold": 2.0, "direction": "below"},
        )
        assert len(result["failed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi):
        """다종목 처리"""
        result = await z_score_condition(
            data=mock_data_multi,
            fields={"lookback": 20, "entry_threshold": 2.0, "direction": "below"},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await z_score_condition(data=[], fields={"lookback": 20})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}", "close": 100 + i}
            for i in range(1, 6)
        ]
        result = await z_score_condition(data=data, fields={"lookback": 20})
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, mock_data_oversold):
        """time_series 출력 형식"""
        result = await z_score_condition(
            data=mock_data_oversold,
            fields={"lookback": 20, "entry_threshold": 2.0, "direction": "below"},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "z_score" in row
                assert "mean" in row
                assert "std" in row

    def test_schema(self):
        """스키마 검증"""
        assert Z_SCORE_SCHEMA.id == "ZScore"
        assert Z_SCORE_SCHEMA.version == "1.0.0"
        assert "lookback" in Z_SCORE_SCHEMA.fields_schema
        assert "entry_threshold" in Z_SCORE_SCHEMA.fields_schema
        assert "exit_threshold" in Z_SCORE_SCHEMA.fields_schema
        assert "direction" in Z_SCORE_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

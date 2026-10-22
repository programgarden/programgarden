"""
Stochastic Oscillator 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.stochastic import (
    stochastic_condition,
    calculate_stochastic_k,
    calculate_stochastic_series,
    STOCHASTIC_SCHEMA,
)


class TestStochasticPlugin:
    """Stochastic 플러그인 테스트"""

    @pytest.fixture
    def mock_symbols(self):
        """테스트용 종목 리스트"""
        return [
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "NVDA", "exchange": "NASDAQ"},
        ]

    @pytest.fixture
    def mock_data_oversold(self):
        """과매도 상태 데이터 (K < 20)"""
        data = []
        # AAPL: 하락 추세 -> 과매도 진입
        price = 200.0
        for i in range(30):
            # 점진적 하락
            price = price * 0.98
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000000,
            })
        return data

    @pytest.fixture
    def mock_data_overbought(self):
        """과매수 상태 데이터 (K > 80)"""
        data = []
        # NVDA: 상승 추세 -> 과매수 진입
        price = 100.0
        for i in range(30):
            # 점진적 상승
            price = price * 1.02
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "NVDA",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": 2000000,
            })
        return data

    @pytest.fixture
    def mock_data_normal(self):
        """일반 상태 데이터"""
        data = []
        price = 150.0
        for i in range(30):
            # 약간의 변동
            if i % 2 == 0:
                price = price * 1.005
            else:
                price = price * 0.995
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000000,
            })
        return data

    def test_calculate_stochastic_k(self):
        """스토캐스틱 %K 계산 테스트"""
        # 14일간 가격 데이터 (상승 추세)
        highs = [100 + i for i in range(14)]  # 100 ~ 113
        lows = [95 + i for i in range(14)]    # 95 ~ 108
        closes = [98 + i for i in range(14)]  # 98 ~ 111

        k = calculate_stochastic_k(highs, lows, closes, period=14)

        # K = (111 - 95) / (113 - 95) * 100 = 88.89
        assert 85 < k < 95, f"Expected K around 88.89, got {k}"

    def test_calculate_stochastic_k_insufficient_data(self):
        """데이터 부족 시 기본값 반환"""
        highs = [100, 101, 102]
        lows = [98, 99, 100]
        closes = [99, 100, 101]

        k = calculate_stochastic_k(highs, lows, closes, period=14)
        assert k == 50.0, "Insufficient data should return 50.0"

    def test_calculate_stochastic_series(self):
        """스토캐스틱 시계열 계산 테스트"""
        # 20일간 데이터 (k_period=14, d_period=3 -> 최소 16일 필요)
        highs = [100 + i * 0.5 for i in range(20)]
        lows = [95 + i * 0.5 for i in range(20)]
        closes = [98 + i * 0.5 for i in range(20)]

        series = calculate_stochastic_series(highs, lows, closes, k_period=14, d_period=3)

        assert len(series) > 0, "Should return non-empty series"

        for entry in series:
            assert "k" in entry
            assert "d" in entry
            assert 0 <= entry["k"] <= 100
            assert 0 <= entry["d"] <= 100

    @pytest.mark.asyncio
    async def test_oversold_condition(self, mock_data_oversold):
        """과매도 조건 테스트"""
        result = await stochastic_condition(
            data=mock_data_oversold,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_overbought_condition(self, mock_data_overbought):
        """과매수 조건 테스트"""
        result = await stochastic_condition(
            data=mock_data_overbought,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "overbought",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_normal):
        """symbol_results 형식 확인"""
        result = await stochastic_condition(
            data=mock_data_normal,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            # k, d 값 또는 error
            if "error" not in sr:
                assert "k" in sr
                assert "d" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_data_normal):
        """values의 time_series 형식 확인"""
        result = await stochastic_condition(
            data=mock_data_normal,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
        )

        assert len(result["values"]) >= 1

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val

            if val["time_series"]:
                for row in val["time_series"]:
                    assert "k" in row
                    assert "d" in row

    @pytest.mark.asyncio
    async def test_auto_extract_symbols(self, mock_data_normal):
        """symbols 없이 data에서 자동 추출"""
        result = await stochastic_condition(
            data=mock_data_normal,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
        )

        assert len(result["symbol_results"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await stochastic_condition(
            data=[],
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 케이스"""
        # 10일 데이터 (최소 16일 필요: k_period=14 + d_period=3 - 1)
        data = []
        for i in range(10):
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

        result = await stochastic_condition(
            data=data,
            fields={
                "k_period": 14,
                "d_period": 3,
                "threshold": 20,
                "direction": "oversold",
            },
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        # 데이터 부족으로 실패해야 함
        assert len(result["failed_symbols"]) == 1
        assert result["result"] is False

    def test_schema(self):
        """스키마 검증"""
        assert STOCHASTIC_SCHEMA.id == "Stochastic"
        assert STOCHASTIC_SCHEMA.version == "1.0.0"
        assert "k_period" in STOCHASTIC_SCHEMA.fields_schema
        assert "d_period" in STOCHASTIC_SCHEMA.fields_schema
        assert "threshold" in STOCHASTIC_SCHEMA.fields_schema
        assert "direction" in STOCHASTIC_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

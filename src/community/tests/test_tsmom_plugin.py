"""
TimeSeriesMomentum (TSMOM) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.time_series_momentum import (
    time_series_momentum_condition,
    calculate_tsmom,
    TSMOM_SCHEMA,
)


def _make_data(symbol: str, exchange: str, n: int, start_price: float = 100.0, trend: float = 0.5) -> list:
    """테스트용 가격 데이터 생성"""
    data = []
    price = start_price
    for i in range(n):
        data.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"2024{(i // 30 + 1):02d}{(i % 30 + 1):02d}",
            "close": round(price, 2),
            "volume": 1000000,
        })
        price += trend
    return data


class TestTSMOMCalculation:
    """calculate_tsmom 단위 테스트"""

    def test_positive_momentum(self):
        """상승 추세 → long 신호"""
        closes = [100.0 + i for i in range(254)]  # 꾸준히 상승
        result = calculate_tsmom(closes, lookback_days=252)
        assert result is not None
        assert result["signal"] == "long"
        assert result["momentum_return"] > 0

    def test_negative_momentum(self):
        """하락 추세 → short 신호"""
        closes = [200.0 - i for i in range(254)]  # 꾸준히 하락
        result = calculate_tsmom(closes, lookback_days=252)
        assert result is not None
        assert result["signal"] == "short"
        assert result["momentum_return"] < 0

    def test_insufficient_data(self):
        """데이터 부족 → None 반환"""
        closes = [100.0] * 100
        result = calculate_tsmom(closes, lookback_days=252)
        assert result is None

    def test_binary_mode(self):
        """binary 모드: 1.0 또는 -1.0 신호"""
        closes = [100.0 + i * 0.5 for i in range(300)]
        result = calculate_tsmom(closes, lookback_days=252, signal_mode="binary", volatility_adjust=False)
        assert result is not None
        assert result["vol_adjusted_signal"] in [1.0, -1.0]

    def test_scaled_mode(self):
        """scaled 모드: 수익률 비례 신호"""
        closes = [100.0 + i * 0.5 for i in range(300)]
        result = calculate_tsmom(closes, lookback_days=252, signal_mode="scaled", volatility_adjust=False)
        assert result is not None
        # scaled 모드에서 vol_adjusted_signal은 momentum_return과 가까워야 함 (반올림 허용)
        assert abs(result["vol_adjusted_signal"] - result["momentum_return"]) < 1e-3

    def test_volatility_adjust_clamp(self):
        """변동성 조정: [-2, 2] 범위 내"""
        closes = [100.0 + i * 5 for i in range(300)]  # 높은 수익률
        result = calculate_tsmom(closes, lookback_days=252, volatility_adjust=True, vol_target=0.15)
        assert result is not None
        assert -2.0 <= result["vol_adjusted_signal"] <= 2.0

    def test_momentum_return_calculation(self):
        """수익률 계산 정확성 검증"""
        # price 100에서 시작, 252일 후 110 → return = 10%
        closes = [100.0] * 252 + [110.0]
        result = calculate_tsmom(closes, lookback_days=252)
        assert result is not None
        assert abs(result["momentum_return"] - 0.1) < 1e-4


class TestTSMOMCondition:
    """time_series_momentum_condition 통합 테스트"""

    @pytest.fixture
    def uptrend_data(self):
        return _make_data("AAPL", "NASDAQ", 300, start_price=100.0, trend=0.5)

    @pytest.fixture
    def downtrend_data(self):
        return _make_data("TSLA", "NASDAQ", 300, start_price=300.0, trend=-0.5)

    @pytest.fixture
    def multi_symbol_data(self):
        return (
            _make_data("AAPL", "NASDAQ", 300, start_price=100.0, trend=0.5)
            + _make_data("TSLA", "NASDAQ", 300, start_price=300.0, trend=-0.5)
        )

    @pytest.mark.asyncio
    async def test_uptrend_passes(self, uptrend_data):
        """상승 추세 → passed_symbols에 포함"""
        result = await time_series_momentum_condition(
            data=uptrend_data,
            fields={"lookback_days": 252},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1
        assert result["passed_symbols"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_downtrend_fails(self, downtrend_data):
        """하락 추세 → failed_symbols에 포함"""
        result = await time_series_momentum_condition(
            data=downtrend_data,
            fields={"lookback_days": 252},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self, multi_symbol_data):
        """다종목: 상승 1개, 하락 1개"""
        result = await time_series_momentum_condition(
            data=multi_symbol_data,
            fields={"lookback_days": 252},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["passed_symbols"]) == 1
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터 → result False"""
        result = await time_series_momentum_condition(data=[], fields={})
        assert result["result"] is False
        assert result["passed_symbols"] == []

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 → failed_symbols"""
        data = _make_data("AAPL", "NASDAQ", 100, trend=0.5)
        result = await time_series_momentum_condition(
            data=data,
            fields={"lookback_days": 252},
        )
        assert len(result["failed_symbols"]) == 1
        assert "error" in result["symbol_results"][0]

    @pytest.mark.asyncio
    async def test_output_format(self, uptrend_data):
        """출력 형식 검증"""
        result = await time_series_momentum_condition(
            data=uptrend_data,
            fields={"lookback_days": 252},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "analysis" in result

        sr = result["symbol_results"][0]
        assert "symbol" in sr
        assert "exchange" in sr
        assert "momentum_return" in sr
        assert "signal" in sr
        assert "vol_adjusted_signal" in sr

    @pytest.mark.asyncio
    async def test_values_time_series(self, uptrend_data):
        """values에 time_series 포함"""
        result = await time_series_momentum_condition(
            data=uptrend_data,
            fields={"lookback_days": 252},
        )
        assert len(result["values"]) == 1
        assert "time_series" in result["values"][0]

    @pytest.mark.asyncio
    async def test_short_lookback(self, uptrend_data):
        """짧은 lookback_days (20일)"""
        result = await time_series_momentum_condition(
            data=uptrend_data,
            fields={"lookback_days": 20},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_vol_adjust_false(self, uptrend_data):
        """변동성 조정 비활성화"""
        result = await time_series_momentum_condition(
            data=uptrend_data,
            fields={"lookback_days": 252, "volatility_adjust": False},
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["momentum_return"] is not None

    def test_schema_validation(self):
        """스키마 검증"""
        assert TSMOM_SCHEMA.id == "TimeSeriesMomentum"
        assert TSMOM_SCHEMA.version == "1.0.0"
        assert "lookback_days" in TSMOM_SCHEMA.fields_schema
        assert "signal_mode" in TSMOM_SCHEMA.fields_schema
        assert "volatility_adjust" in TSMOM_SCHEMA.fields_schema
        assert "vol_target" in TSMOM_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

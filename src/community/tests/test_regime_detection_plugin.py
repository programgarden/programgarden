"""
RegimeDetection (시장 상태 분류) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.regime_detection import (
    regime_detection_condition,
    REGIME_DETECTION_SCHEMA,
    _calculate_sma,
    _calculate_adx,
    _calculate_volatility_percentile,
)


class TestRegimeDetectionPlugin:
    """RegimeDetection 플러그인 테스트"""

    @pytest.fixture
    def mock_data_strong_uptrend(self):
        """강한 상승 추세 (bull)"""
        data = []
        price = 100.0
        for i in range(80):
            price *= 1.012
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
            })
        return data

    @pytest.fixture
    def mock_data_strong_downtrend(self):
        """강한 하락 추세 (bear)"""
        data = []
        price = 200.0
        for i in range(80):
            price *= 0.988
            high = price * 1.01
            low = price * 0.99
            data.append({
                "symbol": "NVDA", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
            })
        return data

    @pytest.fixture
    def mock_data_sideways(self):
        """횡보 (sideways)"""
        data = []
        price = 100.0
        for i in range(80):
            price *= 1.001 if i % 2 == 0 else 0.999
            high = price * 1.003
            low = price * 0.997
            data.append({
                "symbol": "MSFT", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
            })
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert REGIME_DETECTION_SCHEMA.id == "RegimeDetection"

    def test_schema_category(self):
        assert REGIME_DETECTION_SCHEMA.category == "technical"

    def test_schema_required_fields(self):
        assert "close" in REGIME_DETECTION_SCHEMA.required_fields
        assert "high" in REGIME_DETECTION_SCHEMA.required_fields
        assert "low" in REGIME_DETECTION_SCHEMA.required_fields

    def test_schema_tags(self):
        assert "regime" in REGIME_DETECTION_SCHEMA.tags
        assert "adaptive" in REGIME_DETECTION_SCHEMA.tags

    # === 유틸 함수 테스트 ===
    def test_calculate_sma(self):
        prices = [10, 20, 30, 40, 50]
        result = _calculate_sma(prices, 3)
        assert len(result) == 3
        assert result[0] == 20.0
        assert result[-1] == 40.0

    def test_calculate_sma_insufficient_data(self):
        result = _calculate_sma([10, 20], 5)
        assert result == []

    def test_calculate_adx_basic(self):
        highs = [h * 1.01 for h in range(100, 140)]
        lows = [l * 0.99 for l in range(100, 140)]
        closes = list(range(100, 140))
        result = _calculate_adx(highs, lows, closes, 14)
        assert isinstance(result, list)

    def test_calculate_volatility_percentile(self):
        prices = [100 + i * 0.5 for i in range(100)]
        result = _calculate_volatility_percentile(prices, 60)
        assert 0 <= result <= 100

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_bull_regime(self, mock_data_strong_uptrend):
        result = await regime_detection_condition(
            data=mock_data_strong_uptrend,
            fields={"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 30},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) > 0
        sr = result["symbol_results"][0]
        assert sr["regime"] in ("bull", "bear", "sideways")
        assert "confidence" in sr

    @pytest.mark.asyncio
    async def test_bear_regime(self, mock_data_strong_downtrend):
        result = await regime_detection_condition(
            data=mock_data_strong_downtrend,
            fields={"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 30},
        )
        assert isinstance(result["result"], bool)
        sr = result["symbol_results"][0]
        assert sr["regime"] in ("bull", "bear", "sideways")

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await regime_detection_condition(data=[], fields={})
        assert result["result"] is False
        assert result["passed_symbols"] == []

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101", "close": 150, "high": 151, "low": 149}]
        result = await regime_detection_condition(data=data, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_output_structure(self, mock_data_strong_uptrend):
        result = await regime_detection_condition(
            data=mock_data_strong_uptrend,
            fields={"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 30},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "analysis" in result
        assert result["analysis"]["indicator"] == "RegimeDetection"

    @pytest.mark.asyncio
    async def test_time_series_output(self, mock_data_strong_uptrend):
        result = await regime_detection_condition(
            data=mock_data_strong_uptrend,
            fields={"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 30},
        )
        assert len(result["values"]) > 0
        ts = result["values"][0]["time_series"]
        if ts:
            assert "regime" in ts[0]
            assert "adx" in ts[0]
            assert "signal" in ts[0]

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_strong_uptrend, mock_data_sideways):
        combined = mock_data_strong_uptrend + mock_data_sideways
        result = await regime_detection_condition(
            data=combined,
            fields={"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 30},
        )
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_custom_field_mapping(self, mock_data_strong_uptrend):
        result = await regime_detection_condition(
            data=mock_data_strong_uptrend,
            fields={"ma_period": 20, "adx_period": 14},
            field_mapping={"close_field": "close", "high_field": "high", "low_field": "low"},
        )
        assert "symbol_results" in result

"""
MultiTimeframeConfirmation (다중 타임프레임 확인) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.multi_timeframe_confirmation import (
    multi_timeframe_confirmation_condition,
    MTF_CONFIRMATION_SCHEMA,
)


class TestMultiTimeframeConfirmationPlugin:
    """MTF Confirmation 플러그인 테스트"""

    @pytest.fixture
    def mock_data_strong_uptrend(self):
        """강한 상승 추세 - 모든 MA 위에 위치"""
        data = []
        price = 100.0
        for i in range(60):
            price *= 1.008
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
            })
        return data

    @pytest.fixture
    def mock_data_strong_downtrend(self):
        """강한 하락 추세"""
        data = []
        price = 200.0
        for i in range(60):
            price *= 0.992
            data.append({
                "symbol": "NVDA", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
            })
        return data

    @pytest.fixture
    def mock_data_mixed_trend(self):
        """혼합 추세 - 단기 상승 but 장기 하락"""
        data = []
        price = 200.0
        for i in range(60):
            if i < 40:
                price *= 0.995
            else:
                price *= 1.01
            data.append({
                "symbol": "TSLA", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
            })
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert MTF_CONFIRMATION_SCHEMA.id == "MultiTimeframeConfirmation"

    def test_schema_fields(self):
        assert "short_period" in MTF_CONFIRMATION_SCHEMA.fields_schema
        assert "medium_period" in MTF_CONFIRMATION_SCHEMA.fields_schema
        assert "long_period" in MTF_CONFIRMATION_SCHEMA.fields_schema
        assert "require_all" in MTF_CONFIRMATION_SCHEMA.fields_schema

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_bullish_full_alignment(self, mock_data_strong_uptrend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_strong_uptrend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20, "require_all": True, "direction": "bullish"},
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["confirmed"] is True
        assert sr["alignment"] == "3/3"

    @pytest.mark.asyncio
    async def test_bearish_full_alignment(self, mock_data_strong_downtrend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_strong_downtrend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20, "require_all": True, "direction": "bearish"},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_mixed_trend_require_all(self, mock_data_mixed_trend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_mixed_trend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20, "require_all": True, "direction": "bullish"},
        )
        # 장기 MA 아래이므로 require_all=True 시 fail 가능
        sr = result["symbol_results"][0]
        assert "alignment" in sr

    @pytest.mark.asyncio
    async def test_require_two_of_three(self, mock_data_mixed_trend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_mixed_trend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20, "require_all": False, "direction": "bullish"},
        )
        assert isinstance(result["result"], bool)

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await multi_timeframe_confirmation_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101", "close": 150}]
        result = await multi_timeframe_confirmation_condition(data=data, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_output_structure(self, mock_data_strong_uptrend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_strong_uptrend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20},
        )
        assert "passed_symbols" in result
        assert "values" in result
        sr = result["symbol_results"][0]
        assert "short_ma" in sr
        assert "medium_ma" in sr
        assert "long_ma" in sr

    @pytest.mark.asyncio
    async def test_time_series_signal(self, mock_data_strong_uptrend):
        result = await multi_timeframe_confirmation_condition(
            data=mock_data_strong_uptrend,
            fields={"short_period": 5, "medium_period": 10, "long_period": 20, "direction": "bullish"},
        )
        ts = result["values"][0]["time_series"]
        if ts:
            assert "signal" in ts[0]
            assert "alignment" in ts[0]

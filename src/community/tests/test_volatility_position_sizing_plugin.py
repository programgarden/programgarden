"""
VolatilityPositionSizing (변동성 포지션 사이징) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.volatility_position_sizing import (
    volatility_position_sizing_condition,
    VOLATILITY_POSITION_SIZING_SCHEMA,
    _calculate_realized_volatility,
)


class TestVolatilityPositionSizingPlugin:
    """VolatilityPositionSizing 플러그인 테스트"""

    @pytest.fixture
    def mock_data_mixed_volatility(self):
        """변동성 다른 2종목 (AAPL=저변동, TSLA=고변동)"""
        data = []
        aapl_price, tsla_price = 150.0, 200.0
        for i in range(30):
            aapl_price *= 1.003 if i % 2 == 0 else 0.997  # 저변동
            tsla_price *= 1.02 if i % 2 == 0 else 0.98    # 고변동
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
        return data

    @pytest.fixture
    def mock_data_single_symbol(self):
        """단일 종목"""
        data = []
        price = 150.0
        for i in range(30):
            price *= 1.005 if i % 2 == 0 else 0.995
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
            })
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert VOLATILITY_POSITION_SIZING_SCHEMA.id == "VolatilityPositionSizing"

    def test_schema_category(self):
        assert VOLATILITY_POSITION_SIZING_SCHEMA.category == "position"

    def test_schema_fields(self):
        assert "target_volatility" in VOLATILITY_POSITION_SIZING_SCHEMA.fields_schema
        assert "scaling_method" in VOLATILITY_POSITION_SIZING_SCHEMA.fields_schema

    # === 유틸 함수 테스트 ===
    def test_calculate_realized_volatility(self):
        prices = [100 + i * 0.5 for i in range(30)]
        vol = _calculate_realized_volatility(prices, 20)
        assert vol > 0

    def test_calculate_realized_volatility_insufficient_data(self):
        vol = _calculate_realized_volatility([100, 101], 20)
        assert vol == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_inverse_vol_sizing(self, mock_data_mixed_volatility):
        result = await volatility_position_sizing_condition(
            data=mock_data_mixed_volatility,
            fields={"vol_lookback": 20, "scaling_method": "inverse_vol", "max_position_pct": 50, "min_position_pct": 5},
        )
        assert result["result"] is True
        # 저변동 AAPL > 고변동 TSLA 비중
        aapl_result = next(sr for sr in result["symbol_results"] if sr["symbol"] == "AAPL")
        tsla_result = next(sr for sr in result["symbol_results"] if sr["symbol"] == "TSLA")
        assert aapl_result["position_pct"] > tsla_result["position_pct"]

    @pytest.mark.asyncio
    async def test_vol_target_sizing(self, mock_data_mixed_volatility):
        result = await volatility_position_sizing_condition(
            data=mock_data_mixed_volatility,
            fields={"vol_lookback": 20, "scaling_method": "vol_target", "target_volatility": 15.0},
        )
        assert result["result"] is True
        for sr in result["symbol_results"]:
            assert "position_pct" in sr
            assert "volatility" in sr

    @pytest.mark.asyncio
    async def test_equal_risk_sizing(self, mock_data_mixed_volatility):
        result = await volatility_position_sizing_condition(
            data=mock_data_mixed_volatility,
            fields={"vol_lookback": 20, "scaling_method": "equal_risk"},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_max_min_position_clamp(self, mock_data_mixed_volatility):
        result = await volatility_position_sizing_condition(
            data=mock_data_mixed_volatility,
            fields={"vol_lookback": 20, "max_position_pct": 30, "min_position_pct": 10},
        )
        for sr in result["symbol_results"]:
            assert 10 <= sr["position_pct"] <= 30

    @pytest.mark.asyncio
    async def test_single_symbol(self, mock_data_single_symbol):
        result = await volatility_position_sizing_condition(
            data=mock_data_single_symbol,
            fields={"vol_lookback": 20},
        )
        assert result["result"] is True
        assert len(result["symbol_results"]) == 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await volatility_position_sizing_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_mixed_volatility):
        result = await volatility_position_sizing_condition(
            data=mock_data_mixed_volatility,
            fields={"vol_lookback": 20, "target_volatility": 15.0},
        )
        assert result["analysis"]["indicator"] == "VolatilityPositionSizing"
        assert result["analysis"]["total_symbols"] == 2

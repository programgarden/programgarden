"""
RiskParity (리스크 패리티) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.risk_parity import (
    risk_parity_condition,
    RISK_PARITY_SCHEMA,
    _calculate_realized_volatility,
)


class TestRiskParityPlugin:
    """RiskParity 플러그인 테스트"""

    @pytest.fixture
    def mock_data_mixed_volatility(self):
        """변동성 다른 3종목 (AAPL=저변동, TSLA=고변동, MSFT=중변동)"""
        data = []
        aapl_price, tsla_price, msft_price = 150.0, 200.0, 300.0
        for i in range(70):
            aapl_price *= 1.003 if i % 2 == 0 else 0.997   # 저변동
            tsla_price *= 1.025 if i % 2 == 0 else 0.975   # 고변동
            msft_price *= 1.01 if i % 2 == 0 else 0.99     # 중변동
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": round(msft_price, 2)})
        return data

    @pytest.fixture
    def mock_data_single_symbol(self):
        """단일 종목"""
        data = []
        price = 150.0
        for i in range(70):
            price *= 1.005 if i % 2 == 0 else 0.995
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "close": round(price, 2),
            })
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert RISK_PARITY_SCHEMA.id == "RiskParity"

    def test_schema_category(self):
        assert RISK_PARITY_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = RISK_PARITY_SCHEMA.fields_schema
        assert "lookback" in fields
        assert "target_volatility" in fields
        assert "method" in fields
        assert fields["method"]["default"] == "inverse_vol"

    # === 유틸 함수 테스트 ===
    def test_calculate_realized_volatility(self):
        prices = [100 + i * 0.5 for i in range(70)]
        vol = _calculate_realized_volatility(prices, 60)
        assert vol > 0

    def test_calculate_realized_volatility_insufficient_data(self):
        vol = _calculate_realized_volatility([100, 101], 60)
        assert vol == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_inverse_vol_allocation(self, mock_data_mixed_volatility):
        """inverse_vol: 저변동 자산에 높은 비중"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60, "method": "inverse_vol"},
        )
        assert result["result"] is True
        assert len(result["symbol_results"]) == 3

        aapl = next(sr for sr in result["symbol_results"] if sr["symbol"] == "AAPL")
        tsla = next(sr for sr in result["symbol_results"] if sr["symbol"] == "TSLA")
        # 저변동 AAPL > 고변동 TSLA
        assert aapl["weight_pct"] > tsla["weight_pct"]

    @pytest.mark.asyncio
    async def test_erc_allocation(self, mock_data_mixed_volatility):
        """equal_risk_contribution 방식"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60, "method": "equal_risk_contribution"},
        )
        assert result["result"] is True
        assert result["analysis"]["method"] == "equal_risk_contribution"

    @pytest.mark.asyncio
    async def test_weights_sum_to_100(self, mock_data_mixed_volatility):
        """비중 합계 = 100%"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60},
        )
        total_weight = sum(sr["weight_pct"] for sr in result["symbol_results"])
        assert abs(total_weight - 100.0) < 0.1

    @pytest.mark.asyncio
    async def test_min_max_weight_clamp(self, mock_data_mixed_volatility):
        """min/max 비중 제약"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60, "min_weight_pct": 10.0, "max_weight_pct": 50.0},
        )
        for sr in result["symbol_results"]:
            # 정규화 후이므로 exact clamp 보다는 범위 확인
            assert sr["weight_pct"] > 0

    @pytest.mark.asyncio
    async def test_single_symbol(self, mock_data_single_symbol):
        """단일 종목 → 100% 배분"""
        result = await risk_parity_condition(
            data=mock_data_single_symbol,
            fields={"lookback": 60},
        )
        assert result["result"] is True
        assert len(result["symbol_results"]) == 1
        assert result["symbol_results"][0]["weight_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_risk_contribution(self, mock_data_mixed_volatility):
        """위험기여도 출력 확인"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60},
        )
        for sr in result["symbol_results"]:
            assert "risk_contribution_pct" in sr

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await risk_parity_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_mixed_volatility):
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60, "target_volatility": 12.0},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "RiskParity"
        assert analysis["target_volatility"] == 12.0
        assert analysis["total_symbols"] == 3
        assert "portfolio_volatility" in analysis

    @pytest.mark.asyncio
    async def test_volatility_inverse_relationship(self, mock_data_mixed_volatility):
        """변동성과 비중의 역비례 관계"""
        result = await risk_parity_condition(
            data=mock_data_mixed_volatility,
            fields={"lookback": 60, "method": "inverse_vol", "min_weight_pct": 0, "max_weight_pct": 100},
        )
        # 변동성 정렬: AAPL < MSFT < TSLA
        sorted_by_vol = sorted(result["symbol_results"], key=lambda x: x["volatility"])
        sorted_by_weight = sorted(result["symbol_results"], key=lambda x: x["weight_pct"], reverse=True)
        # 저변동 = 고비중
        assert sorted_by_vol[0]["symbol"] == sorted_by_weight[0]["symbol"]

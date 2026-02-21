"""
KellyCriterion (켈리 기준) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.kelly_criterion import (
    kelly_criterion_condition,
    KELLY_CRITERION_SCHEMA,
    _calculate_kelly_pct,
)


class TestKellyCriterionPlugin:
    """KellyCriterion 플러그인 테스트"""

    @pytest.fixture
    def mock_data_trending(self):
        """상승 추세 데이터 (높은 승률)"""
        data = []
        price = 100.0
        for i in range(70):
            # 60% 상승, 40% 하락 (높은 승률)
            if i % 5 < 3:
                price *= 1.015
            else:
                price *= 0.008 + 0.992  # 약 0.8% 하락
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_data_losing(self):
        """하락 추세 데이터 (음의 기대값)"""
        data = []
        price = 100.0
        for i in range(70):
            # 30% 상승, 70% 하락 (낮은 승률)
            if i % 10 < 3:
                price *= 1.005
            else:
                price *= 0.99
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "LOSE", "exchange": "NYSE", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_data_two_symbols(self):
        """2종목 데이터"""
        data = []
        aapl_price, msft_price = 150.0, 300.0
        for i in range(70):
            if i % 3 < 2:
                aapl_price *= 1.01
                msft_price *= 1.008
            else:
                aapl_price *= 0.995
                msft_price *= 0.997
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": round(msft_price, 2)})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert KELLY_CRITERION_SCHEMA.id == "KellyCriterion"

    def test_schema_category(self):
        assert KELLY_CRITERION_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = KELLY_CRITERION_SCHEMA.fields_schema
        assert "lookback" in fields
        assert "kelly_fraction" in fields
        assert "return_period" in fields
        assert fields["kelly_fraction"]["default"] == 0.25

    # === 헬퍼 함수 테스트 ===
    def test_calculate_kelly_pct_positive(self):
        """승률 60%, 손익비 1.5 → 양의 켈리"""
        # 60% wins at +1.5%, 40% losses at -1%
        returns = [0.015] * 6 + [-0.01] * 4
        kelly = _calculate_kelly_pct(returns)
        assert kelly > 0
        assert kelly < 1

    def test_calculate_kelly_pct_negative(self):
        """승률 낮고 손익비 낮으면 0 반환"""
        # 30% wins at +0.5%, 70% losses at -1%
        returns = [0.005] * 3 + [-0.01] * 7
        kelly = _calculate_kelly_pct(returns)
        assert kelly == 0.0

    def test_calculate_kelly_pct_empty(self):
        assert _calculate_kelly_pct([]) == 0.0

    def test_calculate_kelly_pct_no_losses(self):
        """손실 없으면 0 반환 (payoff ratio 계산 불가)"""
        returns = [0.01, 0.02, 0.015]
        kelly = _calculate_kelly_pct(returns)
        assert kelly == 0.0

    def test_calculate_kelly_pct_no_wins(self):
        """수익 없으면 0 반환"""
        returns = [-0.01, -0.02, -0.015]
        kelly = _calculate_kelly_pct(returns)
        assert kelly == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_basic_kelly(self, mock_data_trending):
        result = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "kelly_fraction": 0.25},
        )
        assert result["result"] is True
        assert len(result["symbol_results"]) == 1
        sr = result["symbol_results"][0]
        assert sr["symbol"] == "AAPL"
        assert "kelly_pct" in sr
        assert "fractional_kelly_pct" in sr
        assert "position_pct" in sr
        assert "win_rate" in sr

    @pytest.mark.asyncio
    async def test_negative_expectation(self, mock_data_losing):
        """음의 기대값 종목도 최소 비중 적용"""
        result = await kelly_criterion_condition(
            data=mock_data_losing,
            fields={"lookback": 60, "kelly_fraction": 0.25, "min_position_pct": 2.0},
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["position_pct"] >= 2.0

    @pytest.mark.asyncio
    async def test_fraction_applied(self, mock_data_trending):
        """kelly_fraction이 적용되는지 검증"""
        result_full = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "kelly_fraction": 1.0, "min_position_pct": 0, "max_position_pct": 100},
        )
        result_quarter = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "kelly_fraction": 0.25, "min_position_pct": 0, "max_position_pct": 100},
        )
        full_kelly = result_full["symbol_results"][0]["fractional_kelly_pct"]
        quarter_kelly = result_quarter["symbol_results"][0]["fractional_kelly_pct"]
        # quarter kelly는 full의 25%
        assert abs(quarter_kelly - full_kelly * 0.25) < 0.01

    @pytest.mark.asyncio
    async def test_position_clamp(self, mock_data_trending):
        """min/max clamp 검증"""
        result = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "min_position_pct": 5.0, "max_position_pct": 10.0},
        )
        for sr in result["symbol_results"]:
            assert 5.0 <= sr["position_pct"] <= 10.0

    @pytest.mark.asyncio
    async def test_weekly_returns(self, mock_data_trending):
        """주간 수익률 모드"""
        result = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "return_period": "weekly"},
        )
        assert result["result"] is True
        assert result["analysis"]["return_period"] == "weekly"

    @pytest.mark.asyncio
    async def test_two_symbols(self, mock_data_two_symbols):
        result = await kelly_criterion_condition(
            data=mock_data_two_symbols,
            fields={"lookback": 60},
        )
        assert result["result"] is True
        assert len(result["symbol_results"]) == 2
        assert result["analysis"]["total_symbols"] == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await kelly_criterion_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260101", "close": 150}]
        result = await kelly_criterion_condition(data=data, fields={"lookback": 60})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_trending):
        result = await kelly_criterion_condition(
            data=mock_data_trending,
            fields={"lookback": 60, "kelly_fraction": 0.5},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "KellyCriterion"
        assert analysis["lookback"] == 60
        assert analysis["kelly_fraction"] == 0.5

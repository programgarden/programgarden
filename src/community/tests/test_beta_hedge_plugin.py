"""
BetaHedge (베타 헷지) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.beta_hedge import (
    beta_hedge_condition,
    BETA_HEDGE_SCHEMA,
    _calculate_beta,
    _calculate_returns,
)


class MockRiskTracker:
    def __init__(self):
        self.state = {}
        self.events = []

    def get_state(self, key):
        return self.state.get(key)

    def set_state(self, key, value):
        self.state[key] = value

    def record_event(self, event_type, symbol, data):
        self.events.append({"event_type": event_type, "symbol": symbol, "data": data})


class MockContext:
    def __init__(self):
        self.risk_tracker = MockRiskTracker()


class TestBetaHedgePlugin:
    """BetaHedge 플러그인 테스트"""

    @pytest.fixture
    def mock_data_with_market(self):
        """SPY + 고베타(TSLA) + 저베타(JNJ) 3종목"""
        data = []
        spy_price, tsla_price, jnj_price = 450.0, 200.0, 160.0
        for i in range(130):
            # SPY: 기본 시장 움직임
            market_move = 0.005 if i % 3 < 2 else -0.003
            spy_price *= (1 + market_move)
            # TSLA: 고베타 (시장의 2배 움직임)
            tsla_price *= (1 + market_move * 2.0 + 0.001)
            # JNJ: 저베타 (시장의 0.5배 움직임)
            jnj_price *= (1 + market_move * 0.5 + 0.0005)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "SPY", "exchange": "NYSE", "date": date, "close": round(spy_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
            data.append({"symbol": "JNJ", "exchange": "NYSE", "date": date, "close": round(jnj_price, 2)})
        return data

    @pytest.fixture
    def mock_data_no_market(self):
        """시장 심볼 없는 데이터"""
        data = []
        price = 150.0
        for i in range(130):
            price *= 1.005 if i % 2 == 0 else 0.995
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_positions(self):
        return [
            {"symbol": "TSLA", "current_price": 250.0, "qty": 100},
            {"symbol": "JNJ", "current_price": 165.0, "qty": 200},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert BETA_HEDGE_SCHEMA.id == "BetaHedge"

    def test_schema_category(self):
        assert BETA_HEDGE_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = BETA_HEDGE_SCHEMA.fields_schema
        assert "market_symbol" in fields
        assert "target_beta" in fields
        assert "hedge_method" in fields
        assert fields["lookback"]["default"] == 120

    # === 헬퍼 함수 테스트 ===
    def test_calculate_returns(self):
        prices = [100, 105, 103, 108]
        returns = _calculate_returns(prices)
        assert len(returns) == 3
        assert abs(returns[0] - 0.05) < 0.001

    def test_calculate_returns_empty(self):
        assert _calculate_returns([]) == []
        assert _calculate_returns([100]) == []

    def test_calculate_beta_market_itself(self):
        """시장 자체의 베타 = 1.0"""
        market_returns = [0.01, -0.005, 0.008, -0.003, 0.012, -0.007, 0.005, 0.003, -0.01, 0.006]
        beta = _calculate_beta(market_returns, market_returns)
        assert abs(beta - 1.0) < 0.001

    def test_calculate_beta_high_beta(self):
        """고베타 주식 (시장의 2배 움직임)"""
        market_returns = [0.01, -0.005, 0.008, -0.003, 0.012, -0.007, 0.005, 0.003, -0.01, 0.006]
        stock_returns = [r * 2 for r in market_returns]
        beta = _calculate_beta(stock_returns, market_returns)
        assert abs(beta - 2.0) < 0.001

    def test_calculate_beta_insufficient(self):
        assert _calculate_beta([0.01], [0.01]) == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_basic_beta_calculation(self, mock_data_with_market):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
        )
        assert len(result["symbol_results"]) == 2  # TSLA, JNJ (SPY 제외)
        tsla = next(sr for sr in result["symbol_results"] if sr["symbol"] == "TSLA")
        jnj = next(sr for sr in result["symbol_results"] if sr["symbol"] == "JNJ")
        # TSLA 베타 > JNJ 베타
        assert tsla["beta"] > jnj["beta"]

    @pytest.mark.asyncio
    async def test_portfolio_beta_with_positions(self, mock_data_with_market, mock_positions):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=mock_positions,
        )
        assert "portfolio_beta" in result["analysis"]
        assert result["analysis"]["portfolio_beta"] != 0

    @pytest.mark.asyncio
    async def test_hedge_needed_detection(self, mock_data_with_market):
        """목표 베타를 매우 낮게 설정 → 헷지 필요"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
            },
        )
        assert result["analysis"]["hedge_needed"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_hedge_needed(self, mock_data_with_market):
        """넓은 tolerance → 헷지 불필요"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 1.0, "beta_tolerance": 5.0,
            },
        )
        assert result["analysis"]["hedge_needed"] is False
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_inverse_etf_recommendation(self, mock_data_with_market):
        """인버스 ETF 헷지 추천"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
                "hedge_method": "long_inverse_etf", "inverse_etf_symbol": "SH",
            },
        )
        if result["analysis"]["hedge_needed"]:
            assert "hedge_recommendation" in result
            rec = result["hedge_recommendation"]
            assert rec["action"] == "buy_inverse_etf"
            assert rec["inverse_etf"] == "SH"
            assert rec["suggested_allocation_pct"] > 0

    @pytest.mark.asyncio
    async def test_reduce_high_beta_recommendation(self, mock_data_with_market):
        """고베타 종목 축소 추천"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
                "hedge_method": "reduce_high_beta",
            },
        )
        if result["analysis"]["hedge_needed"]:
            assert "hedge_recommendation" in result
            rec = result["hedge_recommendation"]
            assert rec["action"] == "reduce_high_beta"
            assert rec["target_symbol"] == "TSLA"  # 가장 높은 베타

    @pytest.mark.asyncio
    async def test_market_symbol_not_found(self, mock_data_no_market):
        """시장 심볼 누락 → 에러"""
        result = await beta_hedge_condition(
            data=mock_data_no_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
        )
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_risk_event_recording(self, mock_data_with_market):
        ctx = MockContext()
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
            },
            context=ctx,
        )
        if result["analysis"]["hedge_needed"]:
            assert len(ctx.risk_tracker.events) > 0
            assert ctx.risk_tracker.events[0]["event_type"] == "beta_deviation"
            assert ctx.risk_tracker.state.get("portfolio_beta") is not None

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await beta_hedge_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_with_market):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY", "target_beta": 0.8},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "BetaHedge"
        assert analysis["market_symbol"] == "SPY"
        assert analysis["target_beta"] == 0.8
        assert "portfolio_beta" in analysis
        assert "hedge_needed" in analysis

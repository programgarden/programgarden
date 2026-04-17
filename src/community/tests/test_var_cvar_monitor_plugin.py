"""
VarCvarMonitor (VaR/CVaR 모니터) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.var_cvar_monitor import (
    var_cvar_monitor_condition,
    VAR_CVAR_MONITOR_SCHEMA,
    _calculate_historical_var,
    _calculate_parametric_var,
)


class MockRiskTracker:
    """mock risk tracker for event recording"""
    def __init__(self):
        self.events = []

    def record_event(self, event_type, symbol, data):
        self.events.append({"event_type": event_type, "symbol": symbol, "data": data})


class MockContext:
    def __init__(self):
        self.risk_tracker = MockRiskTracker()


class TestVarCvarMonitorPlugin:
    """VarCvarMonitor 플러그인 테스트"""

    @pytest.fixture
    def mock_data_volatile(self):
        """변동성 높은 데이터 (VaR 높음)"""
        import random
        random.seed(42)
        data = []
        price = 100.0
        for i in range(70):
            # 높은 변동성: +-3% 변동
            change = random.uniform(-0.03, 0.03)
            price *= (1 + change)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_data_stable(self):
        """변동성 낮은 데이터"""
        data = []
        price = 100.0
        for i in range(70):
            price *= 1.001 if i % 2 == 0 else 0.999
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "BOND", "exchange": "NYSE", "date": date, "close": round(price, 4)})
        return data

    @pytest.fixture
    def mock_data_two_symbols(self):
        """2종목 데이터"""
        import random
        random.seed(42)
        data = []
        aapl_price, tsla_price = 150.0, 200.0
        for i in range(70):
            aapl_price *= 1 + random.uniform(-0.015, 0.015)
            tsla_price *= 1 + random.uniform(-0.03, 0.03)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert VAR_CVAR_MONITOR_SCHEMA.id == "VarCvarMonitor"

    def test_schema_category(self):
        assert VAR_CVAR_MONITOR_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = VAR_CVAR_MONITOR_SCHEMA.fields_schema
        assert "confidence_level" in fields
        assert "var_method" in fields
        assert "alert_threshold_pct" in fields

    # === 헬퍼 함수 테스트 ===
    def test_historical_var(self):
        returns = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.025, 0.015, -0.005]
        var = _calculate_historical_var(returns, 95.0)
        assert var > 0

    def test_parametric_var(self):
        returns = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.025, 0.015, -0.005]
        var = _calculate_parametric_var(returns, 95.0)
        assert var > 0

    def test_historical_var_empty(self):
        assert _calculate_historical_var([], 95.0) == 0.0

    def test_parametric_var_insufficient(self):
        assert _calculate_parametric_var([0.01], 95.0) == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_historical_var_calculation(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "historical"},
        )
        assert len(result["symbol_results"]) == 1
        sr = result["symbol_results"][0]
        assert sr["var_pct"] > 0
        assert sr["cvar_pct"] > 0
        assert "breached" in sr

    @pytest.mark.asyncio
    async def test_parametric_var_calculation(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "parametric"},
        )
        sr = result["symbol_results"][0]
        assert sr["var_pct"] > 0
        assert result["analysis"]["var_method"] == "parametric"

    @pytest.mark.asyncio
    async def test_cvar_geq_var(self, mock_data_volatile):
        """CVaR >= VaR (CVaR는 VaR보다 보수적)"""
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "historical"},
        )
        sr = result["symbol_results"][0]
        assert sr["cvar_pct"] >= sr["var_pct"]

    @pytest.mark.asyncio
    async def test_confidence_levels(self, mock_data_volatile):
        """높은 신뢰수준 → 높은 VaR"""
        result_90 = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 90.0},
        )
        result_99 = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 99.0},
        )
        var_90 = result_90["symbol_results"][0]["var_pct"]
        var_99 = result_99["symbol_results"][0]["var_pct"]
        assert var_99 >= var_90

    @pytest.mark.asyncio
    async def test_time_horizon_scaling(self, mock_data_volatile):
        """N일 VaR = 1일 VaR × sqrt(N)"""
        result_1d = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "time_horizon": 1},
        )
        result_4d = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "time_horizon": 4},
        )
        var_1d = result_1d["symbol_results"][0]["var_pct"]
        var_4d = result_4d["symbol_results"][0]["var_pct"]
        # 4일 VaR ≈ 1일 VaR × 2 (sqrt(4) = 2)
        assert abs(var_4d - var_1d * 2) < var_1d * 0.1

    @pytest.mark.asyncio
    async def test_breach_detection(self, mock_data_volatile):
        """낮은 임계값으로 breach 발생"""
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "alert_threshold_pct": 0.1, "action": "alert_only"},
        )
        assert result["result"] is True
        assert result["analysis"]["breached_count"] > 0

    @pytest.mark.asyncio
    async def test_no_breach(self, mock_data_stable):
        """안정적 데이터 → breach 없음"""
        result = await var_cvar_monitor_condition(
            data=mock_data_stable,
            fields={"lookback": 60, "alert_threshold_pct": 30.0},
        )
        assert result["result"] is False
        assert result["analysis"]["breached_count"] == 0

    @pytest.mark.asyncio
    async def test_portfolio_var_with_positions(self, mock_data_two_symbols):
        """positions 있을 때 달러 VaR 계산"""
        positions = [
            {"symbol": "AAPL", "current_price": 150.0, "qty": 100},
            {"symbol": "TSLA", "current_price": 200.0, "qty": 50},
        ]
        result = await var_cvar_monitor_condition(
            data=mock_data_two_symbols,
            fields={"lookback": 60, "alert_threshold_pct": 0.1},
            positions=positions,
        )
        for sr in result["symbol_results"]:
            if "var_dollar" in sr:
                assert sr["var_dollar"] > 0
                assert sr["position_value"] > 0

    @pytest.mark.asyncio
    async def test_risk_event_recording(self, mock_data_volatile):
        """risk_tracker 이벤트 기록"""
        ctx = MockContext()
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "alert_threshold_pct": 0.1},
            context=ctx,
        )
        if result["result"]:
            assert len(ctx.risk_tracker.events) > 0
            assert ctx.risk_tracker.events[0]["event_type"] == "var_breach"

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await var_cvar_monitor_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 99.0},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "VarCvarMonitor"
        assert analysis["confidence_level"] == 99.0
        assert "portfolio_var_pct" in analysis
        assert "portfolio_cvar_pct" in analysis

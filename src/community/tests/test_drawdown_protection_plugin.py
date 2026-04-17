"""
DrawdownProtection (낙폭 보호) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.drawdown_protection import (
    drawdown_protection_condition,
    DRAWDOWN_PROTECTION_SCHEMA,
    risk_features,
)


class MockHWM:
    def __init__(self, hwm_price, current_price, position_avg_price, drawdown_pct):
        self.hwm_price = hwm_price
        self.current_price = current_price
        self.position_avg_price = position_avg_price
        self.drawdown_pct = drawdown_pct


class MockRiskTracker:
    def __init__(self, hwm_data=None):
        self._hwm_data = hwm_data or {}

    def get_hwm(self, symbol):
        return self._hwm_data.get(symbol)


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestDrawdownProtectionPlugin:
    """DrawdownProtection 플러그인 테스트"""

    @pytest.fixture
    def positions_normal(self):
        return [
            {"symbol": "AAPL", "pnl_rate": 5.0, "current_price": 157.5, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -2.0, "current_price": 392.0, "qty": 5, "market_code": "82"},
        ]

    @pytest.fixture
    def positions_drawdown(self):
        return [
            {"symbol": "AAPL", "pnl_rate": -12.5, "current_price": 131.25, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -15.0, "current_price": 340.0, "qty": 5, "market_code": "82"},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert DRAWDOWN_PROTECTION_SCHEMA.id == "DrawdownProtection"

    def test_schema_category(self):
        assert DRAWDOWN_PROTECTION_SCHEMA.category == "position"

    def test_risk_features(self):
        assert "hwm" in risk_features
        assert "events" in risk_features

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_no_drawdown(self, positions_normal):
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_drawdown_triggered(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_reduce_half_action(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "reduce_half"},
        )
        for sym in result["passed_symbols"]:
            assert "sell_quantity" in sym

    @pytest.mark.asyncio
    async def test_partial_trigger(self):
        positions = [
            {"symbol": "AAPL", "pnl_rate": -5.0, "current_price": 142.5, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -15.0, "current_price": 340.0, "qty": 5, "market_code": "82"},
        ]
        result = await drawdown_protection_condition(
            positions=positions,
            fields={"max_drawdown_pct": -10.0},
        )
        assert len(result["passed_symbols"]) == 1
        assert result["passed_symbols"][0]["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        result = await drawdown_protection_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_with_risk_tracker(self, positions_normal):
        tracker = MockRiskTracker(hwm_data={
            "AAPL": MockHWM(hwm_price=170, current_price=157.5, position_avg_price=150, drawdown_pct=12.0),
            "MSFT": MockHWM(hwm_price=400, current_price=392, position_avg_price=380, drawdown_pct=2.0),
        })
        context = MockContext(risk_tracker=tracker)
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={"max_drawdown_pct": -10.0},
            context=context,
        )
        # AAPL: HWM drawdown = -12% → triggered
        # MSFT: HWM drawdown = -2% → not triggered
        assert len(result["passed_symbols"]) == 1
        assert result["passed_symbols"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_analysis_output(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["analysis"]["indicator"] == "DrawdownProtection"
        assert result["analysis"]["triggered_count"] == 2

    @pytest.mark.asyncio
    async def test_symbol_results_detail(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0},
        )
        for sr in result["symbol_results"]:
            assert "drawdown" in sr
            assert "triggered" in sr
            assert "action" in sr

    @pytest.mark.asyncio
    async def test_exchange_name_mapping(self, positions_normal):
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={},
        )
        for sr in result["symbol_results"]:
            assert sr["exchange"] == "NASDAQ"  # market_code "82" → NASDAQ

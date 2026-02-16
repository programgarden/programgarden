"""
PartialTakeProfit 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.partial_take_profit import (
    partial_take_profit_condition,
    PARTIAL_TAKE_PROFIT_SCHEMA,
)


class MockRiskTracker:
    """strategy_state 모킹"""
    def __init__(self):
        self._state = {}

    async def get_state(self, key):
        return self._state.get(key)

    async def set_state(self, key, value):
        self._state[key] = value

    async def delete_state(self, key):
        self._state.pop(key, None)


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestPartialTakeProfitPlugin:

    @pytest.mark.asyncio
    async def test_level_triggered(self):
        """1단계 익절 트리거"""
        tracker = MockRiskTracker()
        context = MockContext(tracker)

        positions = {
            "AAPL": {"pnl_rate": 6.0, "qty": 100, "market_code": "82"},
        }
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] == 50  # 100 * 50%
        assert sr["level_index"] == 0
        assert sr["remaining_levels"] == 1

    @pytest.mark.asyncio
    async def test_no_level_triggered(self):
        """수익률 부족으로 미트리거"""
        positions = {
            "AAPL": {"pnl_rate": 3.0, "qty": 100, "market_code": "82"},
        }
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_completed_level_skip(self):
        """완료된 단계 건너뛰기"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = {
            "AAPL": {"pnl_rate": 6.0, "qty": 50, "market_code": "82"},
        }
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        # 1단계(idx=0) 완료됨, pnl 6% < 10% (2단계) → 미트리거
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_second_level_triggered(self):
        """2단계 익절 트리거 (1단계 완료 상태)"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = {
            "AAPL": {"pnl_rate": 12.0, "qty": 50, "market_code": "82"},
        }
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["level_index"] == 1
        assert sr["sell_quantity"] == 30  # original_qty(100) * 30%

    @pytest.mark.asyncio
    async def test_position_closed_clears_state(self):
        """포지션 청산 시 상태 삭제"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = {
            "AAPL": {"pnl_rate": 0, "qty": 0, "market_code": "82"},
        }
        await partial_take_profit_condition(positions=positions, fields={}, context=context)
        assert "partial_tp.AAPL.completed_levels" not in tracker._state
        assert "partial_tp.AAPL.original_qty" not in tracker._state

    @pytest.mark.asyncio
    async def test_without_context(self):
        """context 없이 실행 (상태 관리 없음)"""
        positions = {
            "AAPL": {"pnl_rate": 8.0, "qty": 100, "market_code": "82"},
        }
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        """빈 포지션"""
        result = await partial_take_profit_condition(positions={}, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_levels_json_string(self):
        """levels를 JSON 문자열로 전달"""
        positions = {"AAPL": {"pnl_rate": 6.0, "qty": 100, "market_code": "82"}}
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": '[{"pnl_pct": 5, "sell_pct": 50}]'},
        )
        assert "passed_symbols" in result
        assert "analysis" in result

    def test_schema(self):
        assert PARTIAL_TAKE_PROFIT_SCHEMA.id == "PartialTakeProfit"
        cat = PARTIAL_TAKE_PROFIT_SCHEMA.category
        assert (cat.value if hasattr(cat, 'value') else cat) == "position"
        assert "levels" in PARTIAL_TAKE_PROFIT_SCHEMA.fields_schema

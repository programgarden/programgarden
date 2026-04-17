"""
TimeBasedExit 플러그인 테스트
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from programgarden_community.plugins.time_based_exit import (
    time_based_exit_condition,
    TIME_BASED_EXIT_SCHEMA,
)


class MockRiskTracker:
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


class TestTimeBasedExitPlugin:

    @pytest.mark.asyncio
    async def test_new_position_records_entry(self):
        """신규 포지션 진입일 기록"""
        tracker = MockRiskTracker()
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5, "warn_days": 0},
            context=context,
        )
        # 오늘 등록 → hold_days=0 → 미트리거
        assert result["result"] is False
        assert "time_exit.AAPL.entry_date" in tracker._state
        sr = result["symbol_results"][0]
        assert sr["hold_days"] == 0
        assert sr["action"] == "hold"

    @pytest.mark.asyncio
    async def test_exit_triggered(self):
        """보유일 초과 시 청산 트리거"""
        tracker = MockRiskTracker()
        entry = (date.today() - timedelta(days=6)).isoformat()
        tracker._state["time_exit.AAPL.entry_date"] = entry
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
            context=context,
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["hold_days"] >= 5
        assert sr["action"] == "exit"

    @pytest.mark.asyncio
    async def test_warn_triggered(self):
        """경고 일수 도달"""
        tracker = MockRiskTracker()
        entry = (date.today() - timedelta(days=4)).isoformat()
        tracker._state["time_exit.AAPL.entry_date"] = entry
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5, "warn_days": 2},
            context=context,
        )
        assert result["result"] is False  # 아직 exit 아님
        sr = result["symbol_results"][0]
        assert sr["warn"] is True
        assert sr["action"] == "warn"

    @pytest.mark.asyncio
    async def test_position_closed_clears_state(self):
        """포지션 청산 시 상태 삭제"""
        tracker = MockRiskTracker()
        tracker._state["time_exit.AAPL.entry_date"] = "2025-01-01"
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 0, "market_code": "82"}]
        await time_based_exit_condition(positions=positions, fields={}, context=context)
        assert "time_exit.AAPL.entry_date" not in tracker._state

    @pytest.mark.asyncio
    async def test_without_context(self):
        """context 없이 실행"""
        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
        )
        # context 없으면 진입일 저장 불가 → 항상 오늘로 기록 → hold_days=0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        """빈 포지션"""
        result = await time_based_exit_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multiple_symbols(self):
        """여러 종목"""
        tracker = MockRiskTracker()
        tracker._state["time_exit.AAPL.entry_date"] = (date.today() - timedelta(days=10)).isoformat()
        tracker._state["time_exit.NVDA.entry_date"] = (date.today() - timedelta(days=2)).isoformat()
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "qty": 100, "market_code": "82"},
            {"symbol": "NVDA", "qty": 50, "market_code": "82"},
        ]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
            context=context,
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1  # AAPL만
        assert result["passed_symbols"][0]["symbol"] == "AAPL"

    def test_schema(self):
        assert TIME_BASED_EXIT_SCHEMA.id == "TimeBasedExit"
        cat = TIME_BASED_EXIT_SCHEMA.category
        assert (cat.value if hasattr(cat, 'value') else cat) == "position"
        assert "max_hold_days" in TIME_BASED_EXIT_SCHEMA.fields_schema
        assert "warn_days" in TIME_BASED_EXIT_SCHEMA.fields_schema

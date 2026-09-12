"""
TimeBasedExit 플러그인 테스트

🔴 이 파일의 ``MockRiskTracker`` 는 **실제 클래스에 없는 메서드를 제공한다** (관측 2026-09-12)
------------------------------------------------------------------------------------------
실제 트래커 ``programgarden.database.workflow_risk_tracker.WorkflowRiskTracker`` 의
실제 인터페이스와 대조한 결과:

| 목이 제공하는 이름 | 실제 클래스 | 비고 |
|---|---|---|
| ``get_state``   | **없음** | 실제 이름은 ``load_state`` (동기) |
| ``set_state``   | **없음** | 실제 이름은 ``save_state`` (동기) |
| ``delete_state``| 있음     | 단 **동기** 메서드 — 플러그인은 ``await`` 한다 |
| ``record_event``| **없음** | 실제 이름은 ``record_risk_event`` |

즉 아래 상태 관련 테스트들은 '플러그인이 라이브에서 실제로 상태를 저장·복원한다'
를 증명하지 않는다 — **목이 약속한 계약대로 플러그인이 호출한다**는 것만 증명한다.
라이브에서는 (가) 실제 트래커를 넘기면 ``AttributeError`` 로 죽고, (나) 애초에
실행기가 positions 기반 플러그인에 ``context`` 를 넘기지 않아 상태 경로가 아예
돌지 않는다(플러그인 모듈 docstring 의 '상태 경로' 절 참조).
목을 실제 시그니처로 맞추는 수정은 이번 회차 범위 밖이다 — 후속 필요.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from programgarden_community.plugins.time_based_exit import (
    time_based_exit_condition,
    TIME_BASED_EXIT_SCHEMA,
)


class MockRiskTracker:
    """strategy_state **목 계약** 모킹 — 실제 WorkflowRiskTracker 인터페이스가 아니다.

    ``get_state``/``set_state`` 는 실제 클래스에 없는 이름이고(실제: ``load_state``/
    ``save_state``, 둘 다 동기), ``delete_state`` 는 이름은 같지만 실제로는 동기
    메서드다. 파일 상단 주석 참조.
    """

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
        """[목 계약 — 라이브 아님] 신규 포지션 진입일 기록"""
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
        """[목 계약 — 라이브 아님] 보유일 초과 시 청산 트리거"""
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
        """[목 계약 — 라이브 아님] 경고 일수 도달"""
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
        """[목 계약 — 라이브 아님] 포지션 청산 시 상태 삭제"""
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
        """[목 계약 — 라이브 아님] 여러 종목"""
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


class TestUnreadableQuantityIsReachable:
    """Z1 — 원값 비교(``if qty <= 0``)가 '수량을 못 읽었다' 를 삼키지 않아야 한다.

    구 코드는 pos_data 원값을 그대로 비교해, 수량이 숫자가 아니면 그 줄에서
    TypeError 로 플러그인 전체가 죽었다(``'n/a' <= 0`` · ``'100' <= 0`` ·
    ``None <= 0`` 모두 TypeError — 직접 실행 확인 2026-09-12). 결과에 사유가
    남을 기회 자체가 없었다.
    """

    @staticmethod
    async def _run(qty):
        return await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": qty, "market_code": "82"}],
            fields={"max_hold_days": 5},
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", ["n/a", None, "", float("nan")])
    async def test_unreadable_quantity_leaves_reason_instead_of_crashing(self, qty):
        result = await self._run(qty)  # 구 코드: TypeError
        sr = result["symbol_results"][0]
        assert sr["action"] == "skip"
        assert "보유 수량을 읽을 수 없어" in sr["reason"]
        assert repr(qty) in sr["reason"]
        assert result["passed_symbols"] == []
        assert result["failed_symbols"][0]["symbol"] == "AAPL"
        # 보유일수를 지어내지 않는다
        assert "hold_days" not in sr

    @pytest.mark.asyncio
    async def test_numeric_string_quantity_is_read_not_crashed(self):
        """'100' 은 읽을 수 있는 수량이다 — 구 코드는 여기서도 TypeError 였다."""
        result = await self._run("100")
        sr = result["symbol_results"][0]
        assert sr["action"] in {"hold", "warn", "exit"}
        assert sr["hold_days"] == 0

    @pytest.mark.asyncio
    async def test_readable_zero_is_still_cleared(self):
        """'0' 과 '못 읽음' 은 다른 사건 — 0 은 종전대로 청산 완료(cleared)."""
        result = await self._run(0)
        sr = result["symbol_results"][0]
        assert sr["action"] == "cleared"
        assert sr["reason"] == "Position closed"

    @pytest.mark.asyncio
    async def test_unreadable_quantity_does_not_delete_entry_date_state(self):
        """[목 계약] 청산인지 알 수 없으므로 진입일 상태를 지우지 않는다."""
        tracker = MockRiskTracker()
        key = "time_exit.AAPL.entry_date"
        tracker._state[key] = (date.today() - timedelta(days=10)).isoformat()
        result = await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": "n/a", "market_code": "82"}],
            fields={"max_hold_days": 5},
            context=MockContext(tracker),
        )
        assert result["symbol_results"][0]["action"] == "skip"
        assert key in tracker._state

    def test_schema_declares_skip_and_reason(self):
        of = TIME_BASED_EXIT_SCHEMA.output_fields
        assert "reason" in of
        assert "skip" in of["action"]["description"]

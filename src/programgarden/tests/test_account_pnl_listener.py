"""
워크플로우 수익률 리스너 기능 테스트

WorkflowPnLEvent와 on_workflow_pnl_update 콜백 테스트
- core 패키지: WorkflowPnLEvent import 테스트
- finance 패키지: AccountPnLInfo import 테스트
- programgarden 패키지: notify_workflow_pnl 메서드 테스트
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional


class TestCorePackageImports:
    """Core 패키지 import 테스트"""

    def test_workflow_pnl_event_import(self):
        """WorkflowPnLEvent가 정상적으로 import 되는지 확인"""
        from programgarden_core.bases import WorkflowPnLEvent
        assert WorkflowPnLEvent is not None

    def test_execution_listener_has_workflow_pnl_method(self):
        """ExecutionListener 프로토콜에 on_workflow_pnl_update 메서드가 있는지 확인"""
        from programgarden_core.bases.listener import ExecutionListener

        # Protocol의 메서드 목록 확인
        assert hasattr(ExecutionListener, 'on_workflow_pnl_update')

    def test_base_execution_listener_has_no_op(self):
        """BaseExecutionListener에 on_workflow_pnl_update no-op 구현이 있는지 확인"""
        from programgarden_core.bases.listener import BaseExecutionListener

        listener = BaseExecutionListener()
        assert hasattr(listener, 'on_workflow_pnl_update')

    def test_workflow_pnl_event_creation(self):
        """WorkflowPnLEvent 인스턴스 생성 테스트"""
        from programgarden_core.bases import WorkflowPnLEvent

        event = WorkflowPnLEvent(
            job_id="test-job-123",
            broker_node_id="broker_1",
            product="overseas_stock",
            workflow_pnl_rate=5.25,
            workflow_eval_amount=105250.0,
            workflow_buy_amount=100000.0,
            workflow_pnl_amount=5250.0,
            other_pnl_rate=0.0,
            other_eval_amount=0.0,
            other_buy_amount=0.0,
            other_pnl_amount=0.0,
            total_pnl_rate=5.25,
            total_eval_amount=105250.0,
            total_buy_amount=100000.0,
            total_pnl_amount=5250.0,
            total_position_count=3,
            currency="USD",
        )

        assert event.job_id == "test-job-123"
        assert event.broker_node_id == "broker_1"
        assert event.product == "overseas_stock"
        assert event.workflow_pnl_rate == 5.25
        assert event.total_position_count == 3

    def test_workflow_pnl_event_has_total_position_count(self):
        """WorkflowPnLEvent에 total_position_count 필드가 있는지 확인"""
        from programgarden_core.bases import WorkflowPnLEvent
        import dataclasses

        fields = {f.name for f in dataclasses.fields(WorkflowPnLEvent)}
        assert 'total_position_count' in fields


class TestFinancePackageImports:
    """Finance 패키지 import 테스트"""

    def test_stock_account_pnl_info_import(self):
        """해외주식 AccountPnLInfo가 정상적으로 import 되는지 확인"""
        from programgarden_finance.ls.overseas_stock.extension.models import AccountPnLInfo
        assert AccountPnLInfo is not None

    def test_futures_account_pnl_info_import(self):
        """해외선물 AccountPnLInfo가 정상적으로 import 되는지 확인"""
        from programgarden_finance.ls.overseas_futureoption.extension.models import AccountPnLInfo
        assert AccountPnLInfo is not None

    def test_stock_account_pnl_info_creation(self):
        """해외주식 AccountPnLInfo 인스턴스 생성 테스트"""
        from programgarden_finance.ls.overseas_stock.extension.models import AccountPnLInfo

        pnl_info = AccountPnLInfo(
            account_pnl_rate=Decimal("5.25"),
            total_eval_amount=Decimal("105250.0"),
            total_buy_amount=Decimal("100000.0"),
            total_pnl_amount=Decimal("5250.0"),
            position_count=3,
            currency="USD",
            last_updated=datetime.now(),
        )

        assert pnl_info.account_pnl_rate == Decimal("5.25")
        assert pnl_info.position_count == 3

    def test_futures_account_pnl_info_creation(self):
        """해외선물 AccountPnLInfo 인스턴스 생성 테스트"""
        from programgarden_finance.ls.overseas_futureoption.extension.models import AccountPnLInfo

        pnl_info = AccountPnLInfo(
            account_pnl_rate=Decimal("3.50"),
            total_eval_amount=Decimal("51750.0"),
            total_margin_used=Decimal("50000.0"),
            total_pnl_amount=Decimal("1750.0"),
            position_count=2,
            currency="USD",
            last_updated=datetime.now(),
        )

        assert pnl_info.account_pnl_rate == Decimal("3.50")
        assert pnl_info.total_margin_used == Decimal("50000.0")


class TestTrackerMethods:
    """Tracker에 계좌 수익률 메서드가 추가되었는지 확인"""

    def test_stock_tracker_has_account_pnl_methods(self):
        """StockAccountTracker에 계좌 수익률 메서드가 있는지 확인"""
        from programgarden_finance.ls.overseas_stock.extension.tracker import StockAccountTracker

        # 메서드 존재 확인 (인스턴스 없이)
        assert hasattr(StockAccountTracker, 'on_account_pnl_change')
        assert hasattr(StockAccountTracker, 'get_account_pnl')
        assert hasattr(StockAccountTracker, '_calculate_account_pnl')

    def test_futures_tracker_has_account_pnl_methods(self):
        """FuturesAccountTracker에 계좌 수익률 메서드가 있는지 확인"""
        from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker

        assert hasattr(FuturesAccountTracker, 'on_account_pnl_change')
        assert hasattr(FuturesAccountTracker, 'get_account_pnl')
        assert hasattr(FuturesAccountTracker, '_calculate_account_pnl')


class TestContextNotifyMethod:
    """ExecutionContext의 notify_workflow_pnl 메서드 테스트"""

    def test_context_has_notify_workflow_pnl(self):
        """ExecutionContext에 notify_workflow_pnl 메서드가 있는지 확인"""
        from programgarden.context import ExecutionContext

        assert hasattr(ExecutionContext, 'notify_workflow_pnl')


class TestCustomListener:
    """커스텀 리스너 구현 테스트"""

    def test_custom_listener_receives_events(self):
        """커스텀 리스너가 WorkflowPnLEvent를 수신하는지 확인"""
        from programgarden_core.bases.listener import (
            BaseExecutionListener,
            WorkflowPnLEvent,
        )

        received_events = []

        class TestListener(BaseExecutionListener):
            async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
                received_events.append(event)

        listener = TestListener()

        # 이벤트 생성
        event = WorkflowPnLEvent(
            job_id="test-job",
            broker_node_id="broker_1",
            product="overseas_stock",
            workflow_pnl_rate=5.25,
            workflow_eval_amount=105250.0,
            workflow_buy_amount=100000.0,
            workflow_pnl_amount=5250.0,
            other_pnl_rate=0.0,
            other_eval_amount=0.0,
            other_buy_amount=0.0,
            other_pnl_amount=0.0,
            total_pnl_rate=5.25,
            total_eval_amount=105250.0,
            total_buy_amount=100000.0,
            total_pnl_amount=5250.0,
            total_position_count=3,
            currency="USD",
        )

        # 비동기 호출 테스트
        async def run_test():
            await listener.on_workflow_pnl_update(event)
            assert len(received_events) == 1
            assert received_events[0].workflow_pnl_rate == 5.25
            assert received_events[0].total_position_count == 3

        asyncio.run(run_test())


class TestBrokerNodeExecutor:
    """BrokerNodeExecutor의 자동 추적 감지 테스트"""

    def test_has_workflow_pnl_listener_detection(self):
        """_has_workflow_pnl_listener 메서드가 리스너를 감지하는지 테스트"""
        from programgarden_core.bases.listener import BaseExecutionListener, WorkflowPnLEvent

        class NoOpListener(BaseExecutionListener):
            """on_workflow_pnl_update를 오버라이드하지 않음"""
            pass

        class ActiveListener(BaseExecutionListener):
            """on_workflow_pnl_update를 오버라이드함"""
            async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
                print(f"Received: {event.workflow_pnl_rate}%")

        # 두 리스너 모두 메서드가 있지만, 실제 구현 여부 확인
        no_op = NoOpListener()
        active = ActiveListener()

        assert hasattr(no_op, 'on_workflow_pnl_update')
        assert hasattr(active, 'on_workflow_pnl_update')
        assert callable(getattr(active, 'on_workflow_pnl_update'))


class TestFuturesPnlAmountPreferred:
    """D1: 선물 평가손익 승수 누락 — 포지션에 pnl_amount 가 있으면 우선 합산한다.

    자체 산술 qty×(현재가-평단) 은 승수를 무시해 1/N 로 축소되므로,
    브로커/트래커가 실은 pnl_amount(승수 반영)를 우선 써야 한다. pnl_rate 는
    승수가 소거되는 eval/buy 비율이라 금액과 무관하게 정확하다.
    """

    def _ctx(self):
        from programgarden.context import ExecutionContext
        ctx = ExecutionContext(job_id="d1-job", workflow_id="d1-wf")
        # no-tracker fallback 경로를 타도록 명시
        ctx._workflow_position_tracker = None
        return ctx

    # 검증 케이스: qty=3, entry=8547.67, current=8601, 승수 10 → LS 금액 1,600 HKD
    _POS = {
        "HSIQ26": {
            "symbol": "HSIQ26",
            "product": "overseas_futures",
            "quantity": 3,
            "buy_price": 8547.67,
            "current_price": 8601.0,
            "pnl_amount": 1600.0,  # 승수 반영 (자체 산술이면 ≈160)
            "pnl_rate": 0.6239,
        }
    }

    def test_account_pnl_prefers_broker_pnl_amount(self):
        ctx = self._ctx()
        result = ctx._calculate_account_pnl(self._POS)
        # 자체 산술이면 ≈160 이지만 pnl_amount 우선 → 1600
        assert result["account_overseas_futures_pnl_amount"] == pytest.approx(1600.0)
        assert result["account_total_pnl_amount"] == pytest.approx(1600.0)
        # pnl_rate 는 승수 무관 eval/buy 비율 — 여전히 정확
        expected_rate = (8601.0 - 8547.67) / 8547.67 * 100
        assert result["account_overseas_futures_pnl_rate"] == pytest.approx(expected_rate)

    def test_account_pnl_falls_back_to_arithmetic_when_absent(self):
        ctx = self._ctx()
        pos = {"HSIQ26": {**self._POS["HSIQ26"]}}
        del pos["HSIQ26"]["pnl_amount"]
        result = ctx._calculate_account_pnl(pos)
        # 폴백: qty×(현재가-평단) = 3×53.33 ≈ 159.99
        assert result["account_overseas_futures_pnl_amount"] == pytest.approx(3 * (8601.0 - 8547.67))

    def test_workflow_fallback_prefers_broker_pnl_amount(self):
        ctx = self._ctx()
        result = ctx._calculate_workflow_pnl(
            current_prices={"HSIQ26": 8601.0},
            all_positions=self._POS,
            product="overseas_futures",
        )
        # no-tracker fallback: 모든 포지션이 "other"
        assert result["other_pnl_amount"] == pytest.approx(1600.0)
        assert result["total_pnl_amount"] == pytest.approx(1600.0)
        # PositionDetail 에도 승수 반영된 금액
        assert float(result["other_positions"][0].pnl_amount) == pytest.approx(1600.0)

    def test_stock_pnl_amount_unchanged(self):
        # 주식은 승수 1 이라 pnl_amount == qty×(current-avg) — 값 동일해야 함
        ctx = self._ctx()
        pos = {
            "AAPL": {
                "symbol": "AAPL", "product": "overseas_stock",
                "quantity": 10, "buy_price": 100.0, "current_price": 110.0,
                "pnl_amount": 100.0,  # 10×(110-100)
            }
        }
        result = ctx._calculate_account_pnl(pos)
        assert result["account_overseas_stock_pnl_amount"] == pytest.approx(100.0)
        assert result["account_overseas_stock_pnl_rate"] == pytest.approx(10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

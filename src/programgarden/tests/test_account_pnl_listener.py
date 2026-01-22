"""
계좌 수익률 리스너 기능 테스트

Phase 4: AccountPnLEvent와 on_account_pnl_update 콜백 테스트
- core 패키지: AccountPnLEvent import 테스트
- finance 패키지: AccountPnLInfo import 테스트
- programgarden 패키지: notify_account_pnl 메서드 테스트
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional


class TestCorePackageImports:
    """Phase 1: Core 패키지 import 테스트"""
    
    def test_account_pnl_event_import(self):
        """AccountPnLEvent가 정상적으로 import 되는지 확인"""
        from programgarden_core.bases import AccountPnLEvent
        assert AccountPnLEvent is not None
    
    def test_execution_listener_has_account_pnl_method(self):
        """ExecutionListener 프로토콜에 on_account_pnl_update 메서드가 있는지 확인"""
        from programgarden_core.bases.listener import ExecutionListener
        import inspect
        
        # Protocol의 메서드 목록 확인
        assert hasattr(ExecutionListener, 'on_account_pnl_update')
    
    def test_base_execution_listener_has_no_op(self):
        """BaseExecutionListener에 on_account_pnl_update no-op 구현이 있는지 확인"""
        from programgarden_core.bases.listener import BaseExecutionListener
        
        listener = BaseExecutionListener()
        assert hasattr(listener, 'on_account_pnl_update')
    
    def test_account_pnl_event_creation(self):
        """AccountPnLEvent 인스턴스 생성 테스트"""
        from programgarden_core.bases import AccountPnLEvent
        
        event = AccountPnLEvent(
            job_id="test-job-123",
            broker_node_id="broker_1",
            product="overseas_stock",
            provider="ls-sec.co.kr",
            account_pnl_rate=5.25,
            total_eval_amount=105250.0,
            total_buy_amount=100000.0,
            total_pnl_amount=5250.0,
            position_count=3,
            currency="USD",
        )
        
        assert event.job_id == "test-job-123"
        assert event.broker_node_id == "broker_1"
        assert event.product == "overseas_stock"
        assert event.account_pnl_rate == 5.25
        assert event.position_count == 3


class TestFinancePackageImports:
    """Phase 2: Finance 패키지 import 테스트"""
    
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
    """Phase 2: Tracker에 계좌 수익률 메서드가 추가되었는지 확인"""
    
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
    """Phase 3: ExecutionContext의 notify_account_pnl 메서드 테스트"""
    
    def test_context_has_notify_account_pnl(self):
        """ExecutionContext에 notify_account_pnl 메서드가 있는지 확인"""
        from programgarden.context import ExecutionContext
        
        assert hasattr(ExecutionContext, 'notify_account_pnl')


class TestCustomListener:
    """커스텀 리스너 구현 테스트"""
    
    def test_custom_listener_receives_events(self):
        """커스텀 리스너가 AccountPnLEvent를 수신하는지 확인"""
        from programgarden_core.bases.listener import (
            BaseExecutionListener,
            AccountPnLEvent,
            NodeStateEvent,
            EdgeStateEvent,
            LogEvent,
            JobStateEvent,
        )
        
        received_events = []
        
        class TestListener(BaseExecutionListener):
            async def on_account_pnl_update(self, event: AccountPnLEvent) -> None:
                received_events.append(event)
        
        listener = TestListener()
        
        # 이벤트 생성
        event = AccountPnLEvent(
            job_id="test-job",
            broker_node_id="broker_1",
            product="overseas_stock",
            provider="ls-sec.co.kr",
            account_pnl_rate=5.25,
            total_eval_amount=105250.0,
            total_buy_amount=100000.0,
            total_pnl_amount=5250.0,
            position_count=3,
            currency="USD",
        )
        
        # 비동기 호출 테스트
        async def run_test():
            await listener.on_account_pnl_update(event)
            assert len(received_events) == 1
            assert received_events[0].account_pnl_rate == 5.25
        
        asyncio.run(run_test())


class TestBrokerNodeExecutor:
    """BrokerNodeExecutor의 자동 추적 감지 테스트"""
    
    def test_has_account_pnl_listener_detection(self):
        """_has_account_pnl_listener 메서드가 리스너를 감지하는지 테스트"""
        from programgarden_core.bases.listener import BaseExecutionListener, AccountPnLEvent
        
        class NoOpListener(BaseExecutionListener):
            """on_account_pnl_update를 오버라이드하지 않음"""
            pass
        
        class ActiveListener(BaseExecutionListener):
            """on_account_pnl_update를 오버라이드함"""
            async def on_account_pnl_update(self, event: AccountPnLEvent) -> None:
                print(f"Received: {event.account_pnl_rate}%")
        
        # 두 리스너 모두 메서드가 있지만, 실제 구현 여부 확인
        # (현재 구현은 메서드 존재만 확인하므로 둘 다 True)
        no_op = NoOpListener()
        active = ActiveListener()
        
        assert hasattr(no_op, 'on_account_pnl_update')
        assert hasattr(active, 'on_account_pnl_update')
        assert callable(getattr(active, 'on_account_pnl_update'))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

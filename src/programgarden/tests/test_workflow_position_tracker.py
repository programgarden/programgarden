"""WorkflowPositionTracker 테스트"""
import asyncio
import tempfile
from decimal import Decimal
import pytest
from programgarden.database import (
    WorkflowPositionTracker,
    PositionInfo,
    LotInfo,
    AnomalyResult,
    PendingFill,
)


class TestWorkflowPositionTracker:
    """WorkflowPositionTracker 테스트"""

    def test_record_order(self):
        """주문 기록 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            
            assert tracker._check_workflow_order('O1', '20260123')
            assert not tracker._check_workflow_order('O2', '20260123')

    def test_get_statistics(self):
        """통계 조회 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            
            stats = tracker.get_statistics()
            assert stats['workflow_orders'] == 1

    def test_trust_score(self):
        """신뢰도 점수 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            score = tracker.calculate_trust_score()
            assert score == 100

    @pytest.mark.asyncio
    async def test_record_fill_workflow(self):
        """워크플로우 체결 기록 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            
            result = await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')
            assert result == 'workflow'

    @pytest.mark.asyncio
    async def test_record_fill_manual(self):
        """수동 체결 기록 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            
            # CommdaCode != '40'이면 수동 주문
            result = await tracker.record_fill('O2', '20260123', 'NVDA', 'NASDAQ', 'buy', 5, 500.0, '104000000', '10')
            assert result == 'manual'

    @pytest.mark.asyncio
    async def test_get_workflow_positions(self):
        """워크플로우 포지션 조회 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')
            
            positions = tracker.get_workflow_positions()
            assert 'AAPL' in positions
            assert positions['AAPL'].quantity == 10
            assert positions['AAPL'].avg_price == Decimal('150.0')

    @pytest.mark.asyncio
    async def test_calculate_pnl(self):
        """PnL 계산 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')
            await tracker.record_fill('O2', '20260123', 'NVDA', 'NASDAQ', 'buy', 5, 500.0, '104000000', '10')
            
            pnl = tracker.calculate_pnl(
                current_prices={'AAPL': Decimal('155.0'), 'NVDA': Decimal('520.0')},
                all_positions={
                    'AAPL': {'quantity': 10, 'avg_price': 150.0, 'exchange': 'NASDAQ'},
                    'NVDA': {'quantity': 5, 'avg_price': 500.0, 'exchange': 'NASDAQ'},
                }
            )
            
            # AAPL: (155-150)*10 = 50, rate = 50/1500 * 100 = 3.33%
            assert float(pnl['workflow_pnl_rate']) == pytest.approx(3.33, rel=0.01)
            assert pnl['trust_score'] == 100

    @pytest.mark.asyncio
    async def test_fifo_sell(self):
        """FIFO 매도 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            
            # 2번에 나눠서 매수
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 100.0, 'job1', 'node1')
            tracker.record_order('O2', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 120.0, 'job1', 'node1')
            
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 100.0, '100000000', '40')
            await tracker.record_fill('O2', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 120.0, '110000000', '40')
            
            positions = tracker.get_workflow_positions()
            assert positions['AAPL'].quantity == 20
            
            # FIFO 매도: 15주를 150에 매도
            tracker.record_order('O3', '20260123', 'AAPL', 'NASDAQ', 'sell', 15, 150.0, 'job1', 'node1')
            await tracker.record_fill('O3', '20260123', 'AAPL', 'NASDAQ', 'sell', 15, 150.0, '120000000', '40')
            
            # 남은 포지션: 5주 (두번째 로트에서)
            positions = tracker.get_workflow_positions()
            assert positions['AAPL'].quantity == 5
            # 평단가는 두번째 로트의 가격
            assert positions['AAPL'].avg_price == Decimal('120.0')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

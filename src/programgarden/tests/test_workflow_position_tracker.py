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

    def test_trust_score_no_orders(self):
        """워크플로우 거래 없으면 신뢰도 0"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            score = tracker.calculate_trust_score()
            assert score == 0

    def test_trust_score_with_orders(self):
        """워크플로우 거래 있으면 신뢰도 100"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260206', 'AAPL', 'NASDAQ', 'buy', 1, 150.0, 'job1', 'node1')
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

    def test_check_and_reset_initial(self):
        """최초 실행 시 paper_trading 저장 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')

            # 최초 실행: False 반환 (초기화 안됨)
            result = tracker.check_and_reset_if_mode_changed(paper_trading=True)
            assert result is False

            # 동일 모드: False 반환
            result = tracker.check_and_reset_if_mode_changed(paper_trading=True)
            assert result is False

    def test_check_and_reset_mode_change(self):
        """paper_trading 모드 변경 시 데이터 초기화 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')

            # 최초 실행: 모의투자 모드
            tracker.check_and_reset_if_mode_changed(paper_trading=True)

            # 주문 기록
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            assert tracker._check_workflow_order('O1', '20260123')

            # 모드 변경: 모의 → 실전
            result = tracker.check_and_reset_if_mode_changed(paper_trading=False)
            assert result is True

            # 데이터 초기화 확인
            assert not tracker._check_workflow_order('O1', '20260123')

    @pytest.mark.asyncio
    async def test_check_and_reset_preserves_data_on_same_mode(self):
        """동일 모드에서 데이터 유지 테스트"""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')

            # 최초 실행: 실전투자 모드
            tracker.check_and_reset_if_mode_changed(paper_trading=False)

            # 주문 및 체결 기록
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')

            positions = tracker.get_workflow_positions()
            assert 'AAPL' in positions

            # 동일 모드로 재실행
            result = tracker.check_and_reset_if_mode_changed(paper_trading=False)
            assert result is False

            # 데이터 유지 확인
            positions = tracker.get_workflow_positions()
            assert 'AAPL' in positions
            assert positions['AAPL'].quantity == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

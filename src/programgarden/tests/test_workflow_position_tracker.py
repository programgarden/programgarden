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

    def test_trading_mode_separation(self):
        """paper/live 모드별 데이터 분리 테스트"""
        with tempfile.TemporaryDirectory() as d:
            db_path = f'{d}/t.db'

            # paper 모드로 주문
            tracker_paper = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            tracker_paper.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')

            # live 모드로 주문
            tracker_live = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='live')
            tracker_live.record_order('O2', '20260123', 'NVDA', 'NASDAQ', 'buy', 5, 500.0, 'job1', 'node1')

            # paper에서는 paper 주문만 보임
            assert tracker_paper._check_workflow_order('O1', '20260123')
            assert not tracker_paper._check_workflow_order('O2', '20260123')

            # live에서는 live 주문만 보임
            assert tracker_live._check_workflow_order('O2', '20260123')
            assert not tracker_live._check_workflow_order('O1', '20260123')

    @pytest.mark.asyncio
    async def test_mode_switch_preserves_data(self):
        """모드 전환 시 기존 데이터 보존 테스트"""
        with tempfile.TemporaryDirectory() as d:
            db_path = f'{d}/t.db'

            # paper 모드로 주문 및 체결
            tracker_paper = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            tracker_paper.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            await tracker_paper.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')

            positions = tracker_paper.get_workflow_positions()
            assert 'AAPL' in positions
            assert positions['AAPL'].quantity == 10

            # live 모드로 전환
            tracker_live = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='live')

            # live에서는 포지션 없음
            positions = tracker_live.get_workflow_positions()
            assert len(positions) == 0

            # 다시 paper로 돌아오면 데이터 살아있음
            tracker_paper2 = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            positions = tracker_paper2.get_workflow_positions()
            assert 'AAPL' in positions
            assert positions['AAPL'].quantity == 10

    def test_trust_score_per_mode(self):
        """모드별 독립적인 trust_score 테스트"""
        with tempfile.TemporaryDirectory() as d:
            db_path = f'{d}/t.db'

            # paper 모드: 주문 있음 → trust_score 100
            tracker_paper = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            tracker_paper.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 150.0, 'job1', 'node1')
            assert tracker_paper.calculate_trust_score() == 100

            # live 모드: 주문 없음 → trust_score 0
            tracker_live = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='live')
            assert tracker_live.calculate_trust_score() == 0

    def test_statistics_per_mode(self):
        """모드별 통계 분리 테스트"""
        with tempfile.TemporaryDirectory() as d:
            db_path = f'{d}/t.db'

            tracker_paper = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            tracker_paper.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')

            tracker_live = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='live')
            tracker_live.record_order('O2', '20260123', 'NVDA', 'NASDAQ', 'buy', 5, 500.0, 'job1', 'node1')
            tracker_live.record_order('O3', '20260123', 'TSLA', 'NASDAQ', 'buy', 3, 200.0, 'job1', 'node1')

            assert tracker_paper.get_statistics()['workflow_orders'] == 1
            assert tracker_paper.get_statistics()['trading_mode'] == 'paper'
            assert tracker_live.get_statistics()['workflow_orders'] == 2
            assert tracker_live.get_statistics()['trading_mode'] == 'live'

    def test_update_trading_mode(self):
        """update_trading_mode 메타데이터 기록 테스트"""
        with tempfile.TemporaryDirectory() as d:
            db_path = f'{d}/t.db'

            tracker = WorkflowPositionTracker(db_path, 'job1', 'broker1', trading_mode='paper')
            tracker.update_trading_mode('paper')  # 최초 기록

            # 모드 전환해도 데이터 삭제 안됨
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            tracker.update_trading_mode('live')  # live로 전환

            # paper 데이터 여전히 존재
            assert tracker._check_workflow_order('O1', '20260123')  # trading_mode='paper'인 tracker이므로


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

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


class TestFuturesMultiplierInference:
    """BLOCKER: 선물 계약 승수를 브로커 pnl_amount 에서 역산해 FIFO 금액을 스케일.

    검증 케이스: avg=8547.67, cur=8601 (계약당 명목차 53.33), 승수 10.
    자체 산술만이면 workflow/other/total 금액이 1/10 로 축소돼 같은 이벤트 안의
    account_* 값과 자기모순이었다 — 이를 승수 스케일로 해소한다. pnl_rate 는
    eval/buy 비율이라 승수가 소거돼 영향 없음.
    """

    AVG = 8547.67
    CUR = 8601.0
    PER_CONTRACT_RAW = CUR - AVG  # 53.33

    async def _futures_tracker(self, d, wf_qty):
        tracker = WorkflowPositionTracker(
            f'{d}/t.db', 'jobF', 'brokerF', product='overseas_futures'
        )
        tracker.record_order('OF1', '20260810', 'HSIQ26', 'HKEX', 'buy', wf_qty, self.AVG, 'jobF', 'nodeF')
        await tracker.record_fill('OF1', '20260810', 'HSIQ26', 'HKEX', 'buy', wf_qty, self.AVG, '103000000', '40')
        return tracker

    @pytest.mark.asyncio
    async def test_full_ownership_matches_broker_pnl_amount(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 3)
            broker_pnl = 1600.0  # 승수 10 반영된 브로커 값
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(self.CUR))},
                all_positions={'HSIQ26': {
                    'quantity': 3, 'avg_price': self.AVG, 'current_price': self.CUR,
                    'pnl_amount': broker_pnl, 'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            # 자체 산술이면 3×53.33≈160 이지만 승수 역산으로 브로커 1600 과 일치
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(broker_pnl, rel=1e-3)
            assert float(pnl['total_pnl_amount']) == pytest.approx(broker_pnl, rel=1e-3)
            assert float(pnl['other_pnl_amount']) == pytest.approx(0.0, abs=1e-6)
            # pnl_rate 는 승수 무관
            assert float(pnl['workflow_pnl_rate']) == pytest.approx(
                self.PER_CONTRACT_RAW / self.AVG * 100, rel=1e-3
            )

    @pytest.mark.asyncio
    async def test_partial_ownership_wf_plus_other_equals_broker(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 3)  # 워크플로우 3 계약
            total_qty = 5  # 계좌 5 (기타 2)
            mult = 10.0
            broker_pnl = mult * total_qty * self.PER_CONTRACT_RAW  # 2666.5
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(self.CUR))},
                all_positions={'HSIQ26': {
                    'quantity': total_qty, 'avg_price': self.AVG, 'current_price': self.CUR,
                    'pnl_amount': broker_pnl, 'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(mult * 3 * self.PER_CONTRACT_RAW, rel=1e-3)
            assert float(pnl['other_pnl_amount']) == pytest.approx(mult * 2 * self.PER_CONTRACT_RAW, rel=1e-3)
            # wf + other ≈ broker pnl_amount (자기모순 해소)
            assert float(pnl['total_pnl_amount']) == pytest.approx(broker_pnl, rel=1e-3)

    @pytest.mark.asyncio
    async def test_stock_multiplier_one_no_regression(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(
                f'{d}/t.db', 'jobS', 'brokerS', product='overseas_stock'
            )
            tracker.record_order('OS1', '20260810', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'jobS', 'nodeS')
            await tracker.record_fill('OS1', '20260810', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')
            pnl = tracker.calculate_pnl(
                current_prices={'AAPL': Decimal('155.0')},
                all_positions={'AAPL': {
                    'quantity': 10, 'avg_price': 150.0, 'current_price': 155.0,
                    'pnl_amount': 50.0,  # =10×(155-150), 승수 1
                    'exchange': 'NASDAQ',
                }},
            )
            # 승수 1 역산 → 기존 산술과 동일
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(50.0, rel=1e-3)
            assert float(pnl['workflow_pnl_rate']) == pytest.approx(3.33, rel=0.01)

    @pytest.mark.asyncio
    async def test_flat_price_uses_cached_multiplier(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 3)
            # 1) 정상 틱 — 승수 10 을 캐시에 채운다
            tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(self.CUR))},
                all_positions={'HSIQ26': {
                    'quantity': 3, 'avg_price': self.AVG, 'current_price': self.CUR,
                    'pnl_amount': 1600.0, 'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            # 2) 현재가 == 평단 (denom≈0, pnl_amount≈0) — 캐시 승수(10)로 스케일
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(self.AVG))},
                all_positions={'HSIQ26': {
                    'quantity': 3, 'avg_price': self.AVG, 'current_price': self.AVG,
                    'pnl_amount': 0.0, 'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(0.0, abs=1e-6)
            # buy_amount 가 승수(10) 스케일됐는지로 캐시 적용 확인 (mult 1 이면 3×avg)
            assert float(pnl['workflow_buy_amount']) == pytest.approx(10 * 3 * self.AVG, rel=1e-3)

    @pytest.mark.asyncio
    async def test_no_pnl_amount_falls_back_to_arithmetic(self):
        # pnl_amount 미제공 → 승수 미역산 → mult 1 (기존 산술, 회귀 없음)
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 3)
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(self.CUR))},
                all_positions={'HSIQ26': {
                    'quantity': 3, 'avg_price': self.AVG, 'current_price': self.CUR,
                    'exchange': 'HKEX',  # pnl_amount 없음
                }},
            )
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(3 * self.PER_CONTRACT_RAW, rel=1e-3)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

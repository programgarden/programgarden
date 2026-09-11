"""WorkflowPositionTracker 테스트"""
import asyncio
import sqlite3
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
            result = await tracker.record_fill('O2', '20260123', 'NVDA', 'NASDAQ', 'buy', 5, 500.0, '104000000', '85')
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

    async def _futures_tracker(self, d, wf_qty, avg=None):
        avg = self.AVG if avg is None else avg
        tracker = WorkflowPositionTracker(
            f'{d}/t.db', 'jobF', 'brokerF', product='overseas_futures'
        )
        tracker.record_order('OF1', '20260810', 'HSIQ26', 'HKEX', 'buy', wf_qty, avg, 'jobF', 'nodeF')
        await tracker.record_fill('OF1', '20260810', 'HSIQ26', 'HKEX', 'buy', wf_qty, avg, '103000000', '40')
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

    # ── MAJOR-1: 숏 실시간 (side 키) 부호 보정 ──

    @pytest.mark.asyncio
    async def test_short_realtime_side_key_inference_and_sign(self):
        """실시간 트래커 dict 는 direction 이 아니라 side 키를 쓴다. 숏이 올바로
        역산되고(수익 숏 → 양수), workflow total == account 스케일 일치.

        과거엔 side 가 항상 "long" 으로 오라벨돼 역산이 폴백(mult=1)되고 FIFO
        롱-only 산식이라 수익 숏이 음수로 뒤집혔다.
        """
        from programgarden.context import ExecutionContext
        with tempfile.TemporaryDirectory() as d:
            # 워크플로우는 숏을 못 담으므로(FIFO 롱-only) other 버킷에서 검증
            tracker = WorkflowPositionTracker(
                f'{d}/t.db', 'jobSh', 'brokerSh', product='overseas_futures'
            )
            short_avg = 8601.0     # 숏 진입가
            short_cur = 8547.67    # 하락 → 숏 수익
            mult = 10.0
            broker_pnl = mult * 3 * (short_avg - short_cur)  # +1599.9 (수익, 양수)
            snapshot = {'HSIQ26': {
                'quantity': 3, 'avg_price': short_avg, 'current_price': short_cur,
                'pnl_amount': broker_pnl, 'side': 'short',  # direction 아닌 side 키
                'exchange': 'HKEX', 'product': 'overseas_futures',
            }}
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(short_cur))},
                all_positions=snapshot,
            )
            # 수익 숏 → 양수 (자체 산식이면 −159.99 로 부호까지 뒤집힘)
            assert float(pnl['total_pnl_amount']) > 0
            assert float(pnl['total_pnl_amount']) == pytest.approx(broker_pnl, rel=1e-3)
            assert float(pnl['other_pnl_amount']) == pytest.approx(broker_pnl, rel=1e-3)

            # Legacy local arithmetic is not sufficient currency/account-basis
            # evidence for the actual listener's account totals.
            ctx = ExecutionContext(job_id='v', workflow_id='v')
            acct = ctx._calculate_account_pnl(snapshot)
            assert acct['account_overseas_futures_pnl_amount'] is None

    @pytest.mark.asyncio
    async def test_mislabeled_short_as_long_rejects_negative_mult(self):
        # 숏을 "long" 으로 오라벨하면 역산 mult 이 음수 → 밴드 밖 거부 → mult=1 폴백
        # (부호는 여전히 long 로 처리되나, 최소한 승수 폭주는 없음)
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(
                f'{d}/t.db', 'jobSh', 'brokerSh', product='overseas_futures'
            )
            short_avg, short_cur = 8601.0, 8547.67
            broker_pnl = 10.0 * 3 * (short_avg - short_cur)  # +1599.9
            snapshot = {'HSIQ26': {
                'quantity': 3, 'avg_price': short_avg, 'current_price': short_cur,
                'pnl_amount': broker_pnl, 'side': 'long',  # 오라벨
                'exchange': 'HKEX',
            }}
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(short_cur))},
                all_positions=snapshot,
            )
            # mult=1 폴백 → buy≈avg×3 (폭주 없음)
            assert float(pnl['other_buy_amount']) == pytest.approx(short_avg * 3, rel=1e-3)

    # ── MAJOR-2: 승수 역산 안정화 가드 ──

    @pytest.mark.asyncio
    async def test_tiny_price_gap_skips_inference_no_blowup(self):
        """P1 폭주 케이스: 현재가−평단=1.0 (상대차 ≈0.0117% < 0.1%) → 역산 생략,
        캐시 없음 → mult=1 폴백. eval/buy 53× 팽창 없음."""
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 3)  # 워크플로우 3 @ 8547.67
            avg = self.AVG
            cur = avg + 1.0  # gap 1.0 → 역산하면 mult=1600/(1×3)=533 폭주
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(cur))},
                all_positions={'HSIQ26': {
                    'quantity': 3, 'avg_price': avg, 'current_price': cur,
                    'pnl_amount': 1600.0, 'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            # mult=1 폴백: buy≈avg×3 (533× 팽창 아님), pnl=3×1.0=3.0
            assert float(pnl['workflow_buy_amount']) == pytest.approx(avg * 3, rel=1e-3)
            assert float(pnl['workflow_pnl_amount']) == pytest.approx(3.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_multiplier_above_band_rejected(self):
        # 밴드(≤10000) 초과 mult → 거부 → mult=1 폴백 (팽창 없음)
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 1, avg=100.0)
            cur = 110.0  # +10% (gap guard 통과)
            gap = cur - 100.0
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(cur))},
                all_positions={'HSIQ26': {
                    'quantity': 1, 'avg_price': 100.0, 'current_price': cur,
                    'pnl_amount': gap * 50000,  # mult 50000 유도 (>10000)
                    'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            assert float(pnl['workflow_buy_amount']) == pytest.approx(100.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_multiplier_snaps_to_integer(self):
        # 수수료 혼입으로 mult 9.87 → 정수 10 스냅 (상대오차 1.3% < 2%)
        with tempfile.TemporaryDirectory() as d:
            tracker = await self._futures_tracker(d, 1, avg=100.0)
            cur = 110.0  # gap 10, +10%
            pnl = tracker.calculate_pnl(
                current_prices={'HSIQ26': Decimal(str(cur))},
                all_positions={'HSIQ26': {
                    'quantity': 1, 'avg_price': 100.0, 'current_price': cur,
                    'pnl_amount': 98.7,  # mult 9.87 → 10 스냅
                    'direction': 'long', 'exchange': 'HKEX',
                }},
            )
            # 스냅됐으면 buy=100×1×10=1000 (스냅 안 하면 987)
            assert float(pnl['workflow_buy_amount']) == pytest.approx(1000.0, rel=1e-3)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestRateEvidenceGate:
    """🔴 계산할 수 없으면 비율을 **발행하지 않는다**(0 이 아니라 None).

    종전 `else Decimal(0)` 는 "아무것도 안 샀다" 를 "0% 로 측정됐다" 로 바꿔 내보냈다.
    그러면 워크플로우를 시작만 해도 공유 카드가 「참고 데이터」에서 "실측 0.0%" 로 바뀐다.
    선물은 이미 이 원칙으로 고쳐져 있고(`futures_pnl.unavailable_workflow_pnl`) 주식만
    안 따라가 있었다.

    **금액은 한 곳도 바뀌지 않는다** — 전량 청산한 날의 0 은 진짜 0 이고, 모니터링 KPI 는
    합산이라 값 하나만 None 이어도 카드가 통째로 접힌다.
    """

    @pytest.mark.asyncio
    async def test_no_workflow_positions_yields_none_not_zero(self):
        """아무것도 안 산 실행 — 비율 None + 사유, 금액은 0 그대로."""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            pnl = tracker.calculate_pnl(current_prices={}, all_positions={})

            assert pnl['workflow_pnl_rate'] is None
            assert pnl['workflow_rate_unavailable_reason'] == 'no_workflow_positions'
            # 금액 3종은 불변(INV-2)
            assert pnl['workflow_buy_amount'] == Decimal(0)
            assert pnl['workflow_eval_amount'] == Decimal(0)
            assert pnl['workflow_pnl_amount'] == Decimal(0)
            # 키는 **항상 있어야 한다** — 빠지면 상류 `.get(..., 0.0)` 이 0 을 되살린다.
            assert 'workflow_pnl_rate' in pnl

    @pytest.mark.asyncio
    async def test_unobserved_price_yields_none(self):
        """현재가를 못 받으면 평단 폴백으로 손익이 정확히 0 이 된다 — 그건 측정이 아니다."""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 1.41, 'job1', 'node1')
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 1.41, '103000000', '40')

            pnl = tracker.calculate_pnl(
                current_prices={},  # 🔴 현재가 미관측
                all_positions={'AAPL': {'quantity': 1, 'avg_price': 1.41, 'exchange': 'NASDAQ'}},
            )
            assert pnl['workflow_pnl_rate'] is None
            assert pnl['workflow_rate_unavailable_reason'] == 'price_unreported'
            # 매수금액은 여전히 관측값이다 — 비우지 않는다.
            assert pnl['workflow_buy_amount'] > 0

    @pytest.mark.asyncio
    async def test_partial_unpriced_does_not_publish_inflated_rate(self):
        """🔴 여러 종목 중 **하나만** 미관측이어도 합계 비율은 부풀려진다 → 발행 금지.

        이게 서버 경계 가드가 못 잡는 구멍이다(그쪽은 정확히 0.0 인 값만 접는다).
        """
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            for i, (sym, px) in enumerate((('AAPL', 150.0), ('NVDA', 500.0))):
                tracker.record_order(f'O{i}', '20260123', sym, 'NASDAQ', 'buy', 10, px, 'job1', 'node1')
                await tracker.record_fill(f'O{i}', '20260123', sym, 'NASDAQ', 'buy', 10, px, '103000000', '40')

            pnl = tracker.calculate_pnl(
                current_prices={'AAPL': Decimal('155.0')},  # NVDA 만 미관측
                all_positions={
                    'AAPL': {'quantity': 10, 'avg_price': 150.0, 'exchange': 'NASDAQ'},
                    'NVDA': {'quantity': 10, 'avg_price': 500.0, 'exchange': 'NASDAQ'},
                },
            )
            assert pnl['workflow_pnl_rate'] is None
            assert pnl['workflow_rate_unavailable_reason'] == 'price_unreported'

    @pytest.mark.asyncio
    async def test_fully_observed_still_publishes_the_rate(self):
        """근거가 다 있으면 종전과 **똑같이** 값을 낸다(회귀 가드)."""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')

            pnl = tracker.calculate_pnl(
                current_prices={'AAPL': Decimal('155.0')},
                all_positions={'AAPL': {'quantity': 10, 'avg_price': 150.0, 'exchange': 'NASDAQ'}},
            )
            assert float(pnl['workflow_pnl_rate']) == pytest.approx(3.33, rel=0.01)
            assert pnl['workflow_rate_unavailable_reason'] is None

    @pytest.mark.asyncio
    async def test_per_position_rate_is_untouched(self):
        """per-position `pnl_rate` 는 이번 범위가 아니다 — listener 계약이 non-Optional 이고
        소비처(DSL 표현식·화면)가 엔진 밖이라 회귀면을 넓히지 않는다."""
        with tempfile.TemporaryDirectory() as d:
            tracker = WorkflowPositionTracker(f'{d}/t.db', 'job1', 'broker1')
            tracker.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, 'job1', 'node1')
            await tracker.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 10, 150.0, '103000000', '40')

            pnl = tracker.calculate_pnl(
                current_prices={},
                all_positions={'AAPL': {'quantity': 10, 'avg_price': 150.0, 'exchange': 'NASDAQ'}},
            )
            assert pnl['workflow_positions'], "포지션 명세는 그대로 실린다"
            assert pnl['workflow_positions'][0].pnl_rate is not None


class TestMediaCodeClassification:
    """E1: 프레임의 통신매체코드로 계좌 내 타 경로 체결을 가른다.

    우리 주문과 일치하는 체결은 매체코드와 무관하게 workflow 이고(주문 기록이
    권위 있는 소유 신호), 일치하지 않는 체결만 매체코드로 HTS(manual)/타 API 를
    가른다. 빈 매체코드는 "모름"이라 사람의 HTS 로 단정하지 않고 버퍼→unknown_api.
    """

    @pytest.mark.asyncio
    async def test_workflow_order_match_wins_over_non40_media(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n')
            # 우리 체결이 '40' 이 아닌 매체코드로 와도 주문 일치가 우선 → workflow
            result = await t.record_fill('O1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', '41')
            assert result == 'workflow'

    @pytest.mark.asyncio
    async def test_human_media_without_order_is_manual(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            # 일치하는 주문이 없고 매체코드가 사람 채널이면 → manual
            #   표: 85=HTS, 22/23=앱, 00=지점 · 실측(2026-09-12 해외주식 AS1): 51=투혼앱, 03=투혼웹
            for code in ('85', '22', '23', '00', '51', '03'):
                result = await t.record_fill(f'X{code}', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', code)
                assert result == 'manual', code

    @pytest.mark.asyncio
    async def test_api_media_without_order_is_never_manual(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            # 표의 API 코드(41, 43)와 실측 40 은 사람이 아니다 — 버퍼 후 unknown_api
            for code in ('40', '41', '43'):
                assert await t.record_fill(f'A{code}', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', code) == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute("SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api'] * 3

    @pytest.mark.asyncio
    async def test_unlisted_or_broker_side_media_is_other(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            # 96=최종결제 / LP=로스컷 / 표에 없는 값: 추측 분류하지 않고 other
            for code in ('96', 'LP', 'ZZ'):
                assert await t.record_fill(f'O{code}', '20260123', 'AAPL', 'NASDAQ', 'sell', 1, 100.0, '100000000', code) == 'other', code

    @pytest.mark.asyncio
    async def test_empty_media_without_order_buffers_then_unknown_api(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            # 빈 매체코드는 사람의 HTS 로 단정하지 않는다 — 버퍼(늦게 도착할 우리
            # 주문에 대비)했다가, 일치 주문이 없으면 unknown_api 로 접는다(manual 아님).
            result = await t.record_fill('X2', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', '')
            assert result == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                rows = conn.execute("SELECT classification FROM trade_history").fetchall()
            assert rows == [('unknown_api',)]


class TestWorkflowLotOwnershipAndEstimate:
    """E2: workflow 매도는 workflow 로트만 소진하고, 남는 잔량은 계좌 평균매입가로 추정."""

    @pytest.mark.asyncio
    async def test_workflow_sell_consumes_only_workflow_lots(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            # 같은 종목의 수동(HTS) 로트와 workflow 로트가 공존
            await t.record_fill('M1', '20260123', 'AAPL', 'NASDAQ', 'buy', 5, 90.0, '100000000', '85')  # manual (HTS)
            t.record_order('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 3, 100.0, 'j', 'n')
            await t.record_fill('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 3, 100.0, '110000000', '40')  # workflow
            # workflow 매도 2주: workflow 로트(100)만 소진, 수동 로트는 그대로
            t.record_order('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 2, 120.0, 'j', 'n')
            await t.record_fill('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 2, 120.0, '120000000', '40')
            positions = t.get_workflow_positions()
            assert positions['AAPL'].quantity == 1  # workflow 3 중 2 소진 → 1 남음
            with sqlite3.connect(t.db_path) as conn:
                manual_remaining = conn.execute(
                    "SELECT remaining_qty FROM workflow_position_lots WHERE classification='manual'"
                ).fetchone()[0]
            assert manual_remaining == 5  # 수동 로트는 손대지 않음

    @pytest.mark.asyncio
    async def test_workflow_sell_records_account_avg_estimate_for_tail(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n')
            await t.record_fill('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', '40')
            # 3 매도인데 workflow 로트는 1뿐 → 잔량 2를 계좌 평균매입가 105 로 추정
            t.record_order('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 3, 110.0, 'j', 'n')
            await t.record_fill('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 3, 110.0, '110000000', '40',
                                account_avg_price=105.0)
            with sqlite3.connect(t.db_path) as conn:
                realized, unmatched, basis, source, est_pnl = conn.execute(
                    "SELECT realized_pnl, unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl "
                    "FROM trade_history WHERE side='sell'"
                ).fetchone()
            assert realized == pytest.approx(10.0)   # FIFO 매칭분 1 @ (110-100)
            assert unmatched == pytest.approx(2.0)
            assert basis == pytest.approx(105.0)
            assert source == 'account_balance_avg_price'
            assert est_pnl == pytest.approx(10.0)     # (110-105)*2

    @pytest.mark.asyncio
    async def test_workflow_sell_without_account_avg_records_no_estimate(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n')
            await t.record_fill('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, '100000000', '40')
            t.record_order('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 3, 110.0, 'j', 'n')
            await t.record_fill('W2', '20260123', 'AAPL', 'NASDAQ', 'sell', 3, 110.0, '110000000', '40')
            with sqlite3.connect(t.db_path) as conn:
                row = conn.execute(
                    "SELECT unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl "
                    "FROM trade_history WHERE side='sell'"
                ).fetchone()
            assert row == (None, None, None, None)  # 평단 없으면 추정 저장 없음

    @pytest.mark.asyncio
    async def test_non_workflow_sell_still_consumes_any_lot(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            # workflow 매수 로트
            t.record_order('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 5, 100.0, 'j', 'n')
            await t.record_fill('W1', '20260123', 'AAPL', 'NASDAQ', 'buy', 5, 100.0, '100000000', '40')
            # 수동(HTS) 매도: 분류 무관 로트 소진(종전 동작 불변) → workflow 로트를 먹는다
            await t.record_fill('M1', '20260123', 'AAPL', 'NASDAQ', 'sell', 2, 120.0, '110000000', '85')  # HTS 수동 매도
            with sqlite3.connect(t.db_path) as conn:
                wf_remaining = conn.execute(
                    "SELECT remaining_qty FROM workflow_position_lots WHERE classification='workflow'"
                ).fetchone()[0]
            assert wf_remaining == 3  # 수동 매도가 workflow 로트 2주를 소진

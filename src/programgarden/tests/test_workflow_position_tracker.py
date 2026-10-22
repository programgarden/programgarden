"""WorkflowPositionTracker 테스트"""
import asyncio
import sqlite3
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from programgarden.database import (
    WorkflowPositionTracker,
    PositionInfo,
    LotInfo,
    AnomalyResult,
    PendingFill,
)
from programgarden.database.workflow_position_tracker import media_channel


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


class TestOrderDateWindowMatching:
    """T2 후속 — 주문일자 D±1 창의 수용 조건 (2026-09-12 적대적 검토 B1·B2·B5 + 재검증).

    창은 '같은 주문인데 주문일자가 한 칸 어긋난 경우' 를 구제하려고 존재하고, 그 어긋남은
    **양방향 모두 이 저장소에 근거가 있다**:
      · D-1 = AS1/SC1 프레임에 주문일자 필드가 없어 수신 시각의 로컬 날짜를 쓰기 때문
        (설계상). 자정 직전 접수 → 자정 직후 체결.
      · D+1 = LS 가 야간 세션을 전 영업일로 파일링하기 때문(2026-09-10 실측: 00:39:25 KST
        접수(로컬 20260910) → OrdDt 20260909 — tests/test_broker_business_date_window.py
        헤더). record_order 는 로컬 날짜, TC3 체결은 프레임 ordr_dt 라 주문이 하루 뒤다.
    넓힌 경로는 추론이므로 수용 조건이 여섯이다 — 후보 1건 · 종목 일치 · (비교 가능하면)
    매매구분 일치 · **매체코드가 사람 채널이 아닐 것** · **체결 수량 ≤ 주문 수량** ·
    **주문 기록 시각과 체결 수신 시각이 12시간 이내(휴리스틱·보조)**. 종목 대조가 없으면
    우리 원장에 없는 제3자 주문번호가 늘 '후보 1건' 이라 무조건 통과하고, 뒤의 세 가드가
    없으면 **영업일마다 리셋되는 브로커 주문번호가 재발급된 남의 주문**이 종목·side 까지
    같아 그대로 흡수된다. 시각 가드만으로는 못 가른다 — 미국주식은 KST 주간(09:00~)에도
    거래되므로(저장소 메모리 관측 확정) 다음 날 낮 재발급이 우리 주문 몇 시간 뒤일 수 있다.
    """

    @pytest.mark.asyncio
    async def test_previous_day_order_matches_and_resolves_node_id(self):
        """(1) 주문 D-1 / 체결 D, 같은 종목 → workflow 이고 node_id 도 채워진다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            result = await t.record_fill('86382', '20260912', 'AAPL', 'NASDAQ',
                                         'buy', 1, 100.0, '000030000', '40')
            assert result == 'workflow'
            # B2: 분류와 **같은 매처**를 쓰므로 창으로 매칭된 체결도 node_id 가 붙는다.
            # (안 그러면 classification='workflow' + node_id=None 조합이 생겨 하류
            #  멱등 키 job_id:node_id:order_id:seq 의 node 축이 빈 문자열로 접힌다.)
            assert t.lookup_order_identity('86382', '20260912') == ('j', 'node-w')
            # 호출부가 체결 사실을 직접 넘겨도 같은 결과
            assert t.lookup_order_identity('86382', '20260912',
                                           symbol='AAPL', side='buy') == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_previous_day_order_with_other_symbol_is_not_workflow(self):
        """(2) 주문 D-1 / 체결 D 인데 종목이 다르면 workflow 가 아니다 (B1 회귀 가드)."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            result = await t.record_fill('86382', '20260912', 'TSLA', 'NASDAQ',
                                         'sell', 5, 300.0, '000030000', '40')
            assert result == 'pending'          # API 코드 → 버퍼
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                rows = conn.execute(
                    "SELECT classification, symbol FROM trade_history").fetchall()
            assert rows == [('unknown_api', 'TSLA')]
            assert t.lookup_order_identity('86382', '20260912') is None

    @pytest.mark.asyncio
    async def test_side_mismatch_in_window_is_rejected(self):
        """창 후보의 매매구분이 체결과 다르면 거부한다(원장에 side 가 있어 비교 가능)."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            assert await t.record_fill('86382', '20260912', 'AAPL', 'NASDAQ',
                                       'sell', 1, 100.0, '000030000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']

    @pytest.mark.asyncio
    async def test_next_day_order_matches_the_overnight_business_date_fill(self):
        """(M1) 주문 기록 D+1 / 체결 D → workflow 이고 node_id 도 붙는다.

        LS 야간 세션 파일링의 실제 형태다(2026-09-10 실측, 헤더는
        tests/test_broker_business_date_window.py): 00:39 KST 로컬 20260910 접수 주문을
        record_order 가 '20260910' 으로 기록하는데, TC3 체결 프레임의 ordr_dt 는 전
        영업일 '20260909' 로 온다. D-1 팔만 있으면 이 체결은 매칭에 실패해 unknown_api 로
        굳는다 — 이 저장소가 **실측으로 기록한 유일한 방향**이 그쪽이다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('86382', '20260910', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            result = await t.record_fill('86382', '20260909', 'AAPL', 'NASDAQ',
                                         'buy', 1, 100.0, '003925000', '40')
            assert result == 'workflow'
            assert t.lookup_order_identity('86382', '20260909') == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_window_rejects_two_candidates_for_the_same_order_no(self):
        """(4) 창 안에 같은 주문번호 후보가 2건이면 모호해서 거부한다.

        UNIQUE(order_no, order_date) 때문에 **한 날짜**에 같은 주문번호는 1건뿐이라,
        D-1 한 칸짜리 창에서 후보가 2건이 되는 실제 형태는 0 패딩만 다른 재사용
        ('123' 과 '0123')이다. 이 경로(명시 체결번호)는 주문번호를 정규화해 맞추므로
        둘 다 후보가 되고, 후보 수 가드가 둘 다 거부한다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('123', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n1')
            t.record_order('0123', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n2')
            assert await t.record_fill('123', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0,
                                       '000030000', '40', execution_id='E1') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']

    @pytest.mark.asyncio
    async def test_same_order_no_on_both_days_takes_the_exact_date_path(self):
        """같은 주문번호가 D-1·D 양쪽 원장에 있으면 **창까지 가지 않는다**.

        같은 날짜(D) 정확일치가 먼저 성립하므로 그 주문의 node 가 답이다 — 창의 후보
        수 가드가 개입할 여지 자체가 없다(위 테스트가 그 가드를 따로 고정한다).
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-prev')
            t.record_order('86382', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-today')
            assert await t.record_fill('86382', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '40') == 'workflow'
            assert t.lookup_order_identity('86382', '20260912') == ('j', 'node-today')

    @pytest.mark.asyncio
    @pytest.mark.parametrize('order_date', ['20260910', '20260914'])
    async def test_two_days_apart_is_unknown_api(self, order_date):
        """(5) D±2 는 창 밖이다 → unknown_api."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('86382', order_date, 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            assert await t.record_fill('86382', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']

    @pytest.mark.asyncio
    async def test_hts_fill_sharing_a_previous_day_order_no_is_not_absorbed(self):
        """(7) B1 실측 시나리오 재현 — HTS(85) 체결이 우리 D-1 주문번호와 겹쳐도 흡수 안 됨.

        검토자 실측: 우리 D-1 AAPL buy #86382 기록 뒤 다음 날 TSLA sell 5@300 commda=85
        체결을 넣자 classification='workflow' 로 기록되고 FIFO 가 'Sell without enough
        position' 까지 냈다. 이제 종목이 달라 창 매칭이 거부되고, 매체코드 표대로 manual.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            await t.record_fill('86382', '20260911', 'AAPL', 'NASDAQ',
                                'buy', 1, 100.0, '235900000', '40')
            result = await t.record_fill('86382', '20260912', 'TSLA', 'NASDAQ',
                                         'sell', 5, 300.0, '000030000', '85')
            assert result == 'manual'
            with sqlite3.connect(t.db_path) as conn:
                tsla = conn.execute(
                    "SELECT classification FROM trade_history WHERE symbol='TSLA'").fetchall()
                aapl_lot = conn.execute(
                    "SELECT remaining_qty, classification FROM workflow_position_lots "
                    "WHERE symbol='AAPL'").fetchone()
            assert tsla == [('manual',)]
            assert aapl_lot == (1, 'workflow')      # 우리 로트는 그대로

    @pytest.mark.asyncio
    async def test_buffered_fill_matches_previous_day_order_recorded_late(self):
        """체결이 먼저 오고 주문 ACK 가 늦게 기록돼도 ±1일 창(여기선 D-1 방향)으로 이어붙인다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 5.0        # 타임아웃 전에 주문이 기록되는 상황
            assert await t.record_fill('86382', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '40') == 'pending'
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            await asyncio.sleep(0.05)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['workflow']

    @pytest.mark.asyncio
    async def test_buffered_fill_with_other_symbol_is_not_claimed_by_late_order(self):
        """버퍼에 있던 남의 체결은 늦게 기록된 우리 D-1 주문이 데려가지 못한다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.2
            assert await t.record_fill('86382', '20260912', 'TSLA', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '40') == 'pending'
            t.record_order('86382', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            await asyncio.sleep(0.35)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']

    def test_order_date_window_is_one_day_each_way_and_never_raises(self):
        """(M1·B5) 창은 D-1·D+1 두 칸이고, 문자열이 아닌 order_date 로 죽지 않는다."""
        window = WorkflowPositionTracker._order_date_window
        assert window('20260301') == ['20260228', '20260302']   # 2026 은 평년
        assert window('20270101') == ['20261231', '20270102']
        assert window('20261231') == ['20261230', '20270101']
        assert window(20260912) == ['20260911', '20260913']     # 숫자여도 죽지 않는다
        assert window(None) == []
        assert window('') == []
        assert window('2026-09-12') == []              # 형식 이상 → 넓히지 않는다
        assert window(object()) == []                  # AttributeError 로 죽지 않는다

    @pytest.mark.asyncio
    async def test_non_string_order_date_does_not_kill_record_fill(self):
        """(B5) 종전에는 (order_date or '').strip() 이 AttributeError 를 던져 체결 기록 전체가 죽었다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            result = await t.record_fill('O1', 20260912, 'AAPL', 'NASDAQ',
                                         'buy', 1, 100.0, '000030000', '85')
            assert result == 'manual'


def _shift_order_created_at(tracker, order_no, order_date, *, hours):
    """원장에 이미 적힌 주문 기록 시각을 과거로 옮긴다(창 시각 가드 실증용).

    record_order 는 created_at 에 ``datetime.now()`` 를 쓰므로, 테스트에서는 주문과 체결이
    같은 순간에 일어난다. 실제로 갈리는 건 '어제 밤 기록 → 오늘 낮 체결' 이므로 그 간격을
    원장 값으로 직접 만든다(다른 필드는 건드리지 않는다).
    """
    with sqlite3.connect(tracker.db_path) as conn:
        row = conn.execute(
            "SELECT created_at FROM workflow_orders WHERE order_no = ? AND order_date = ?",
            (order_no, order_date)).fetchone()
        moved = (datetime.fromisoformat(row[0]) - timedelta(hours=hours)).isoformat()
        conn.execute(
            "UPDATE workflow_orders SET created_at = ? WHERE order_no = ? AND order_date = ?",
            (moved, order_no, order_date))
        conn.commit()


class TestWidenedWindowReuseGuards:
    """(M2) 브로커 주문번호는 **영업일마다 리셋**된다 — 창 경로에만 가드 둘을 더 건다.

    어제 우리 주문번호가 오늘 사용자 주문에 재발급되고 종목·매매구분까지 같으면 종전
    세 가드(후보 1건·종목·side)를 전부 통과한다. 검토자 실측: 우리 D-1 AAPL buy #3 →
    다음 날 14:00 사용자 HTS 매수 7@250(order_no '3', commda_code '85')이
    classification='workflow' 로 기록되고 workflow_position_lots 에 남의 로트가 생겼다.

    (가) 프레임이 "사람이 낸 주문"이라고 명시한 매체코드면 창 수용을 거부한다.
    (나) 주문 기록 시각과 체결 수신 시각의 간격이 임계(12시간)를 넘으면 거부한다 —
         **휴리스틱(보조)** 이다. 미국주식은 KST 주간(09:00~, Blue Ocean)에도 거래되므로
         (저장소 메모리 관측 확정 2026-09-11) 다음 날 낮 재발급이 우리 주문 몇 시간 뒤일
         수 있어 시각만으로는 못 가른다.
    (다) 체결 수량이 주문 수량(workflow_orders.quantity)을 넘으면 거부한다 — 우리 주문의
         체결(부분·전량)은 주문 수량을 넘을 수 없으므로 우리 체결을 놓치지 않고, 세션
         시각에 의존하지 않는다. 검토자 실측 형태(우리 1주 → 남의 7주)를 (가)(나)가 모두
         통과하는 조건에서도 잡는다.
    셋 다 **창 경로 전용**이다 — 정확일치 경로의 의미는 그대로 둔다.
    """

    @pytest.mark.asyncio
    async def test_hts_reissued_order_no_with_same_symbol_and_side_is_manual(self):
        """(가) 검토자 실측 시나리오가 이제 manual 로 떨어진다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            result = await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                         'buy', 7, 250.0, '140000000', '85')
            assert result == 'manual'
            with sqlite3.connect(t.db_path) as conn:
                lots = conn.execute(
                    "SELECT classification, original_qty FROM workflow_position_lots").fetchall()
                hist = conn.execute("SELECT classification FROM trade_history").fetchall()
            assert lots == [('manual', 7)]      # workflow 로트가 아니다
            assert hist == [('manual',)]
            # 분류와 조회가 같은 판정을 한다(한쪽만 workflow 가 되지 않는다).
            assert t.lookup_order_identity('3', '20260912') is None

    @pytest.mark.asyncio
    async def test_without_the_media_guard_the_hts_reissue_is_absorbed(self, monkeypatch):
        """(가 실증) 매체코드 가드를 빼면 HTS 재발급이 흡수된다.

        나머지 가드(후보 1건·종목·side·수량·시각)를 전부 통과하는 형태로 맞춘다 — 남의
        HTS 주문이 우리 주문과 **같은 수량(1주)** 이고 같은 시간대다. 수량 가드(다)가 들어온
        뒤에도 이 형태는 (가) 만이 막으므로, 그래서 이 가드가 load-bearing 이다.
        (검토자 실측 원형인 7주 체결은 이제 (다)도 막는다 — 그 실증은 아래 (다) 테스트.)
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            monkeypatch.setattr(WorkflowPositionTracker, '_may_widen_for_media',
                                staticmethod(lambda commda_code: True))
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            result = await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                         'buy', 1, 250.0, '140000000', '85')
            assert result == 'workflow'         # 가드 없이는 남의 체결을 흡수한다
            with sqlite3.connect(t.db_path) as conn:
                lots = conn.execute(
                    "SELECT classification, original_qty FROM workflow_position_lots").fetchall()
            assert lots == [('workflow', 1)]

    @pytest.mark.asyncio
    async def test_media_guard_does_not_touch_the_exact_date_path(self):
        """(가) 정확일치 경로의 의미는 그대로 — 사람 매체코드라도 우리 주문이면 workflow.

        우리 OPEN API 주문이 항상 '40' 을 달고 오는 게 아니므로(2026-09-12 AS1 실측에서
        40 이었지만 표에는 41/43 도 있다), 정확일치 경로에서 매체코드로 우리 체결을
        걷어내면 안 된다. 거기선 (주문번호, 주문일자) 동시 일치가 더 강한 증거다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('7', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            assert await t.record_fill('7', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '140000000', '85') == 'workflow'
            assert t.lookup_order_identity('7', '20260912') == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_api_reissue_far_from_the_order_is_refused_by_the_time_guard(self):
        """(나) 매체코드가 사람이 아니어도 시각이 멀면 창 수용을 거부한다.

        (가)(다)가 못 막는 형태 — 재발급된 번호로 들어온 타 API 체결이 우리 주문과 같은
        수량(1주)이다. 주문 기록은 어제 밤, 체결은 오늘 낮(15시간)이라 임계 12시간 밖이다.
        (수량을 1주로 맞춘 건 시각 가드만 고립시키기 위해서다 — 7주면 (다)가 먼저 잡는다.)
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=15)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 250.0, '140000000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']
            assert t.lookup_order_identity('3', '20260912') is None

    @pytest.mark.asyncio
    async def test_time_guard_still_accepts_a_full_session_gap(self):
        """(나 실증) 같은 시나리오라도 간격이 임계 안이면 종전대로 workflow 다.

        미국 정규장 한 세션(KST 22:30~05:00, 6.5시간)만큼 떨어져 있어도 수용한다 —
        가드가 구제 대상(자정/영업일 경계 한 칸)을 죽이지 않는다는 뜻이다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 7, 250.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=6.5)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 7, 250.0, '043000000', '40') == 'workflow'
            assert t.lookup_order_identity('3', '20260912') == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_order_row_without_created_at_is_excluded_from_the_window(self):
        """(나) created_at 이 비어 있는 옛 행은 추론 없이 창 수용에서 제외한다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 7, 250.0, 'j', 'node-w')
            with sqlite3.connect(t.db_path) as conn:
                conn.execute("UPDATE workflow_orders SET created_at = NULL "
                             "WHERE order_no = ? AND order_date = ?", ('3', '20260911'))
                conn.commit()
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 7, 250.0, '000030000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']

    @pytest.mark.asyncio
    async def test_exact_date_path_does_not_need_created_at(self):
        """정확일치 경로는 시각 가드를 타지 않는다 — created_at 이 없어도 workflow."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('7', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            with sqlite3.connect(t.db_path) as conn:
                conn.execute("UPDATE workflow_orders SET created_at = NULL")
                conn.commit()
            assert await t.record_fill('7', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '40') == 'workflow'


class TestWidenedWindowQuantityGuard:
    """(다) 창 경로의 수량 상한 — 체결 수량 ≤ 주문 수량(workflow_orders.quantity).

    오너 지적(2026-09-12): 미국주식은 **KST 주간(09:00~, Blue Ocean)에도 거래된다**(저장소
    메모리 관측 확정 — MARA 거래량 26→938). 그러면 자정 직전 우리 주문 → 다음 날 10:00
    남의 재발급 주문은 10시간이라 시각 가드(12시간) 안이고, 매체코드가 API(40)면 (가)도
    통과한다. 그 형태를 시각과 무관하게 잡는 게 수량 상한이다 — 우리 주문의 체결(부분·
    전량)은 주문 수량을 넘을 수 없으므로 false-miss 가 없다.

    아래 시나리오는 **매체 가드·시각 가드를 모두 통과하는 조건**(commda '40', 간격 3시간)
    으로 고정한다.
    """

    @pytest.mark.asyncio
    async def test_api_reissue_with_more_quantity_than_our_order_is_not_workflow(self):
        """우리 D-1 AAPL buy #3 **1주** → 다음 날 API(40) 같은 번호·종목·방향 **7주**, 3시간
        → workflow 가 아니다(버퍼 → unknown_api). 분류와 조회가 같은 판정을 한다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 7, 250.0, '100000000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                hist = conn.execute(
                    "SELECT classification, quantity FROM trade_history").fetchall()
                lots = conn.execute(
                    "SELECT classification, original_qty FROM workflow_position_lots").fetchall()
            assert hist == [('unknown_api', 7)]
            assert lots == [('unknown_api', 7)]          # workflow 로트가 생기지 않는다
            assert t.lookup_order_identity('3', '20260912') is None
            # 호출부가 체결 사실을 직접 넘겨도 같은 판정
            assert t.lookup_order_identity(
                '3', '20260912', symbol='AAPL', side='buy', commda_code='40',
                received_at=datetime.now(), quantity=7) is None

    @pytest.mark.asyncio
    async def test_same_quantity_in_the_same_conditions_is_workflow(self):
        """대조 — 같은 조건에서 **1주** 체결이면 workflow 이고 node_id 도 붙는다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 250.0, '100000000', '40') == 'workflow'
            assert t.lookup_order_identity('3', '20260912') == ('j', 'node-w')
            assert t.lookup_order_identity(
                '3', '20260912', symbol='AAPL', side='buy', commda_code='40',
                received_at=datetime.now(), quantity=1) == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_partial_fill_in_the_window_is_workflow(self):
        """부분체결 — 주문 3주, 체결 1주 → workflow (수량 상한은 부분체결을 죽이지 않는다)."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 3, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 250.0, '100000000', '40') == 'workflow'
            assert t.lookup_order_identity('3', '20260912') == ('j', 'node-w')

    @pytest.mark.asyncio
    async def test_fractional_fill_in_the_window_is_workflow(self):
        """소수점 주식 — 주문 1, 체결 0.847972 → 통과(float 비교)."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 0.847972, 250.0, '100000000', '40') == 'workflow'
            assert t.lookup_order_identity('3', '20260912') == ('j', 'node-w')

    @pytest.mark.asyncio
    @pytest.mark.parametrize('ledger_quantity', [None, 0])
    async def test_order_row_without_quantity_is_excluded_from_the_window(self, ledger_quantity):
        """원장 수량이 비었거나 0 이면 대조 불가 → 추론 없이 창 수용 거부(unknown_api)."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            with sqlite3.connect(t.db_path) as conn:
                conn.execute("UPDATE workflow_orders SET quantity = ? "
                             "WHERE order_no = ? AND order_date = ?",
                             (ledger_quantity, '3', '20260911'))
                conn.commit()
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 250.0, '100000000', '40') == 'pending'
            await asyncio.sleep(0.15)
            with sqlite3.connect(t.db_path) as conn:
                kinds = [r[0] for r in conn.execute(
                    "SELECT classification FROM trade_history")]
            assert kinds == ['unknown_api']
            assert t.lookup_order_identity('3', '20260912') is None

    @pytest.mark.asyncio
    async def test_without_the_quantity_guard_the_api_reissue_is_absorbed(self, monkeypatch):
        """(다 실증) 수량 가드를 빼면 7주 재발급이 그대로 흡수된다 — load-bearing.

        매체 가드(40 → 통과)·시각 가드(3시간 → 통과)·후보 1건·종목·side 는 이 시나리오를
        못 막는다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            monkeypatch.setattr(WorkflowPositionTracker, '_fill_quantity_within_order',
                                staticmethod(lambda fill_quantity, order_quantity: True))
            t.record_order('3', '20260911', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            _shift_order_created_at(t, '3', '20260911', hours=3)
            assert await t.record_fill('3', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 7, 250.0, '100000000', '40') == 'workflow'
            with sqlite3.connect(t.db_path) as conn:
                lots = conn.execute(
                    "SELECT classification, original_qty FROM workflow_position_lots").fetchall()
            assert lots == [('workflow', 7)]            # 남의 7주가 우리 로트가 된다

    @pytest.mark.asyncio
    async def test_quantity_guard_does_not_touch_the_exact_date_path(self):
        """정확일치 경로는 수량 가드를 타지 않는다 — (주문번호, 주문일자) 동시 일치가 답이다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('7', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'node-w')
            assert await t.record_fill('7', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 7, 100.0, '100000000', '40') == 'workflow'
            assert t.lookup_order_identity('7', '20260912') == ('j', 'node-w')

    @pytest.mark.parametrize('fill_qty, order_qty, expected', [
        (1, 1, True),              # 전량
        (1, 3, True),              # 부분
        (0.847972, 1, True),       # 소수점 주식
        (7, 1, False),             # 주문보다 큰 체결 = 우리 체결일 수 없다
        (Decimal('2'), 2, True),   # Decimal 도 float 로 비교
        (1, None, False),          # 원장 수량 없음 → 추론 없이 거부
        (1, 0, False),             # 원장 수량 0
        (1, -1, False),            # 원장 수량 음수
        (1, 'abc', False),         # 숫자가 아님
        (None, 1, False),          # 체결 수량 없음
        (float('nan'), 1, False),  # 유한하지 않음
        (1, float('inf'), False),
    ])
    def test_fill_quantity_within_order_unit(self, fill_qty, order_qty, expected):
        assert WorkflowPositionTracker._fill_quantity_within_order(fill_qty, order_qty) is expected


class TestMatcherModesAndHotPath:
    """(m1·m3) 주문번호 대조 mode 별 strict 의미와 정확일치 핫패스의 조회 형태."""

    @staticmethod
    def _insert_raw_order(tracker, order_no, order_date, node_id):
        """record_order 를 거치지 않고 원장에 행을 넣는다(깨진 주문번호 재현용)."""
        with sqlite3.connect(tracker.db_path) as conn:
            conn.execute(
                """
                INSERT INTO workflow_orders
                (product, provider, order_no, order_date, symbol, exchange, side,
                 quantity, price, job_id, node_id, trading_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tracker.product, tracker.provider, order_no, order_date, 'AAPL', 'NASDAQ',
                 'buy', 1, 100.0, 'j', node_id, tracker.trading_mode,
                 datetime.now().isoformat()))
            conn.commit()

    def test_unnormalizable_row_does_not_kill_the_whole_lookup(self):
        """(m1) 같은 날짜의 정규화 불가 행 하나가 lookup 전체를 죽이지 않는다.

        통합 전 이 경로는 그 행만 ``except ValueError: continue`` 로 건너뛰었다. strict=True
        로 통합하면 ValueError 가 lookup_order_identity 의 except 로 올라가 **멀쩡한 주문의
        node_id 까지 None** 이 된다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            self._insert_raw_order(t, '000000.5', '20260912', 'node-broken')
            self._insert_raw_order(t, '0000123', '20260912', 'node-x')
            assert t.lookup_order_identity('123', '20260912') == ('j', 'node-x')

    def test_normalized_mode_keeps_its_strict_meaning(self):
        """(m1) 명시 체결번호 경로(mode='normalized')의 strict 의미는 종전 그대로다.

        그 날짜의 우리 주문 기록이 깨졌다는 신호이므로 삼키지 않는다.
        """
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            self._insert_raw_order(t, '000000.5', '20260912', 'node-broken')
            self._insert_raw_order(t, '0000123', '20260912', 'node-x')
            with pytest.raises(ValueError):
                t._match_workflow_order('123', '20260912', mode='normalized')

    def test_exact_date_match_is_an_indexed_equality_query(self, monkeypatch):
        """(m3) 체결 핫패스는 order_no 등가조건 한 방이다 — 날짜 전체 스캔 + 파이썬 루프 금지.

        통합 과정에서 이 단계가 'order_date 로만 좁혀 전부 읽고 파이썬에서 비교' 로 바뀌었다.
        EXPLAIN QUERY PLAN 실측(2026-09-12): order_no 를 포함한 등가조건은
        UNIQUE(order_no, order_date) 인덱스를 등가 탐색하고, order_date 만 거는 형태는
        idx_orders_lookup_v2 를 trading_mode=? 로만 타 그 모드의 행을 전부 훑는다.
        """
        import programgarden.database.workflow_position_tracker as wpt

        statements = []
        real_connect = wpt.sqlite3.connect

        class _SpyConnection:
            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql, *args, **kwargs):
                statements.append(" ".join(str(sql).split()))
                return self._conn.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._conn, name)

            def __enter__(self):
                self._conn.__enter__()
                return self

            def __exit__(self, *args):
                return self._conn.__exit__(*args)

        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.record_order('86382', '20260912', 'AAPL', 'NASDAQ', 'buy', 1, 100.0, 'j', 'n')
            monkeypatch.setattr(wpt.sqlite3, 'connect',
                                lambda *a, **k: _SpyConnection(real_connect(*a, **k)))

            statements.clear()
            assert t._check_workflow_order('86382', '20260912') is True
            assert len(statements) == 1                      # 창 조회조차 하지 않는다
            assert 'AND order_no = ?' in statements[0]        # 인덱스 등가조회
            assert 'order_date IN' not in statements[0]

            statements.clear()
            assert t._check_workflow_order('99999', '20260912') is False
            # 실패했을 때만 창 후보를 끌어온다(정확일치 단계는 여전히 등가조회 한 방).
            assert len(statements) == 2
            assert 'AND order_no = ?' in statements[0]
            assert 'order_date IN' in statements[1]


class TestMediaChannelSingleTable:
    """(6)(B3) 매체코드 표는 상품 분기 없는 **단일 합집합**이다.

    tracker 는 워크플로우당 1개이고 가장 먼저 초기화된 브로커의 product 로 고정되므로,
    표를 상품으로 가르면 해외+국내 혼합 워크플로우에서 반대쪽 시장 체결이 통째로
    오분류된다(85 HTS → other, 43 api → other 라 버퍼도 건너뛴다).
    """

    @pytest.mark.parametrize('code', ['85', '60', '22', '23', '50', '00', '51', '03'])
    def test_human_codes(self, code):
        # 85=HTS(해외 TR 문서/AS1 실측) · 60=HTS · 50=MTS(국내, 오너 진술 2026-09-12,
        # 라이브 미관측) · 22/23=앱(표) · 00=지점 · 51=투혼앱 · 03=투혼웹(실측)
        assert media_channel(code) == 'human'

    @pytest.mark.parametrize('code', ['40', '41', '43'])
    def test_api_codes(self, code):
        assert media_channel(code) == 'api'

    @pytest.mark.parametrize('value', ['', '   ', None])
    def test_blank_is_unknown(self, value):
        assert media_channel(value) == 'unknown'

    @pytest.mark.parametrize('code', ['77', '96', 'LP', 'SK', 'SO'])
    def test_unlisted_or_broker_side_is_other(self, code):
        assert media_channel(code) == 'other'

    def test_takes_no_product_argument(self):
        # 상품 분기를 되돌렸다는 사실 자체를 고정한다(시그니처가 다시 갈리면 실패).
        with pytest.raises(TypeError):
            media_channel('60', 'korea_stock')

    @pytest.mark.asyncio
    async def test_overseas_hts_fill_stays_manual_on_a_korea_scoped_tracker(self):
        """혼합 워크플로우 회귀 가드 — 국내 product 로 고정된 tracker 라도 85 는 사람이다."""
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b', product='korea_stock')
            assert await t.record_fill('H1', '20260912', 'AAPL', 'NASDAQ',
                                       'buy', 1, 100.0, '000030000', '85') == 'manual'


class TestUnknownApiRatioDenominator:
    """(B6) unknown_api 비율의 분모는 리터럴 '40' 이 아니라 media_channel() 기준이다."""

    @pytest.mark.asyncio
    async def test_denominator_follows_the_media_table(self):
        with tempfile.TemporaryDirectory() as d:
            t = WorkflowPositionTracker(f'{d}/t.db', 'j', 'b')
            t.FILL_BUFFER_TIMEOUT = 0.05
            # 우리 체결 — 빈 매체코드(TC3 선물 프레임처럼). 종전 '40' 고정 분모에서는
            # 이런 행이 통째로 빠져 선물은 이 이상탐지가 영구히 0행이었다.
            t.record_order('W1', '20260912', 'ES', 'CME', 'buy', 1, 100.0, 'j', 'n')
            assert await t.record_fill('W1', '20260912', 'ES', 'CME', 'buy', 1, 100.0,
                                       '000030000', '') == 'workflow'
            # 타 API 체결 2건: 빈 코드 1 + 43(Robo API) 1 → 둘 다 분모에 든다
            assert await t.record_fill('X1', '20260912', 'ES', 'CME', 'buy', 1, 100.0,
                                       '000031000', '') == 'pending'
            assert await t.record_fill('X2', '20260912', 'ES', 'CME', 'buy', 1, 100.0,
                                       '000032000', '43') == 'pending'
            # 사람(85)·브로커측(96) 코드는 분모 밖이다
            assert await t.record_fill('H1', '20260912', 'ES', 'CME', 'buy', 1, 100.0,
                                       '000033000', '85') == 'manual'
            assert await t.record_fill('B1', '20260912', 'ES', 'CME', 'buy', 1, 100.0,
                                       '000034000', '96') == 'other'
            await asyncio.sleep(0.15)

            ratios = [a for a in t.detect_anomalies() if a.pattern == 'unknown_api_ratio']
            assert len(ratios) == 1
            # 분모 3 = 빈 코드 2 + '43' 1, 분자 2 = unknown_api. 85/96 은 제외.
            assert '2/3' in ratios[0].description
            assert ratios[0].severity == 20          # 감점 폭은 종전 그대로(최대 20)
            assert t.calculate_trust_score() == 80

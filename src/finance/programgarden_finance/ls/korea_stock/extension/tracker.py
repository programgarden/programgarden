"""
국내주식 계좌 추적기 (KrStockAccountTracker)

실시간 손익/예수금/미체결 주문을 추적합니다.
- 1분 주기 API 갱신
- S3_(KOSPI)/K3_(KOSDAQ) 실시간 틱으로 손익 계산
- SC1 주문체결 시 즉시 갱신
- WebSocket 공유 및 중복 방지
- 계좌 전체 수익률 계산 및 콜백 지원
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import asyncio

from .models import (
    KrStockPositionItem,
    KrStockBalanceInfo,
    KrStockOpenOrder,
    KrCommissionConfig,
    KrAccountPnLInfo,
)
from .calculator import KrStockPnLCalculator
from .subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

# LS증권 API 응답 코드
# - "00000": 공통 성공 코드
# - "00001": 일부 TR 성공 코드
# - "00136": CSPAQ22200 등 SOAP계열 TR 성공 코드
SUCCESS_CODES = {"00000", "00001", "00136"}

# "데이터 없음" 판단 패턴
NO_DATA_PATTERNS = ["없습니다", "없음", "no data", "not found", "조회내역"]

# 성공 메시지 패턴 (rsp_cd가 SUCCESS_CODES에 없더라도 성공으로 판단)
SUCCESS_MSG_PATTERNS = ["조회가 완료", "정상"]


def _is_success_response(rsp_cd: str, rsp_msg: str) -> bool:
    """응답이 성공인지 판단 (rsp_cd 또는 rsp_msg 기준)"""
    if rsp_cd in SUCCESS_CODES:
        return True
    # rsp_cd가 없거나 알 수 없는 코드여도 성공 메시지면 성공으로 판단
    msg = (rsp_msg or "")
    return any(pattern in msg for pattern in SUCCESS_MSG_PATTERNS)


def _is_no_data_response(rsp_cd: str, rsp_msg: str) -> bool:
    """응답이 '데이터 없음' 케이스인지 판단"""
    if _is_success_response(rsp_cd, rsp_msg):
        return False
    msg_lower = (rsp_msg or "").lower()
    return any(pattern in msg_lower for pattern in NO_DATA_PATTERNS)


def _is_kospi_market(marketgb: str) -> bool:
    """KOSPI 시장 여부 (marketgb 필드 기준)"""
    return marketgb in ("1", "10")


class KrStockAccountTracker:
    """
    국내주식 계좌 추적기

    보유종목, 예수금, 미체결 주문을 실시간으로 추적하고
    S3_/K3_ 틱 데이터를 기반으로 손익을 계산합니다.
    """

    DEFAULT_REFRESH_INTERVAL = 60  # 1분
    DEFAULT_ORDER_DELAY = 3  # 체결 후 재조회 대기 시간 (초)

    def __init__(
        self,
        accno_client,
        real_client=None,
        refresh_interval: int = DEFAULT_REFRESH_INTERVAL,
        commission_rate: Optional[Decimal] = None,
    ):
        """
        Args:
            accno_client: 계좌 API 클라이언트 (korea_stock().accno())
            real_client: 실시간 API 클라이언트 (korea_stock().real()) - 필수
            refresh_interval: 주기적 갱신 간격 (초, 기본 60초)
            commission_rate: 수수료율 (None이면 0.015%)
        """
        self._accno_client = accno_client
        self._real_client = real_client
        self._refresh_interval = refresh_interval

        # 수수료/세금 설정
        config_kwargs = {}
        if commission_rate is not None:
            config_kwargs["commission_rate"] = commission_rate
        self._commission_config = KrCommissionConfig(**config_kwargs)

        # 손익 계산기
        self._calculator = KrStockPnLCalculator(self._commission_config)

        # 구독 관리자 (S3_, K3_ 각각)
        self._s3_subscription_manager = SubscriptionManager()
        self._k3_subscription_manager = SubscriptionManager()

        # 데이터 캐시
        self._positions: Dict[str, KrStockPositionItem] = {}
        self._balance: Optional[KrStockBalanceInfo] = None
        self._open_orders: Dict[int, KrStockOpenOrder] = {}
        self._current_prices: Dict[str, int] = {}

        # 계좌 수익률 캐시
        self._account_pnl: Optional[KrAccountPnLInfo] = None

        # t0424 OutBlock 합산 정보 캐시
        self._account_summary: Dict[str, int] = {}

        # 콜백
        self._on_position_change_callbacks: List[Callable] = []
        self._on_balance_change_callbacks: List[Callable] = []
        self._on_open_orders_change_callbacks: List[Callable] = []
        self._on_account_pnl_change_callbacks: List[Callable] = []

        # Task 관리
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # 에러 상태
        self._last_errors: Dict[str, str] = {}

    async def start(self):
        """추적 시작"""
        if self._is_running:
            return

        self._is_running = True
        self._loop = asyncio.get_running_loop()

        # 1. WebSocket 연결 확인
        if not self._real_client:
            raise ValueError(
                "real_client is required. "
                "Please provide real_client=korea_stock().real() when creating tracker."
            )

        if not await self._real_client.is_connected():
            await self._real_client.connect()

        # 2. 초기 데이터 로드
        await self._fetch_all_data()

        # 3. 실시간 구독 설정
        await self._setup_subscriptions()

        # 4. 주기적 갱신 Task 시작
        self._refresh_task = asyncio.create_task(self._periodic_refresh())

    async def stop(self):
        """추적 중지"""
        self._is_running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None

        await self._cleanup_subscriptions()

    # ===== 데이터 조회 =====

    async def _fetch_all_data(self):
        """모든 데이터 조회 (보유종목, 예수금, 미체결)"""
        await self._fetch_positions()
        await asyncio.sleep(2)  # rate limit
        await self._fetch_balance()
        await asyncio.sleep(2)  # rate limit
        await self._fetch_open_orders()

    async def _fetch_positions(self):
        """보유종목 조회 (t0424 주식잔고2)"""
        try:
            from ..accno.t0424.blocks import T0424InBlock

            tr = self._accno_client.t0424(
                body=T0424InBlock(
                    prcgb="2",    # BEP단가
                    chegb="2",    # 체결기준잔고
                    dangb="0",    # 정규장
                    charge="1",   # 제비용포함
                ),
            )
            resp = await tr.req_async()

            rsp_cd = getattr(resp, 'rsp_cd', '')
            rsp_msg = getattr(resp, 'rsp_msg', '')

            if _is_no_data_response(rsp_cd, rsp_msg):
                logger.info(f"[_fetch_positions] 보유종목 없음 (rsp_cd={rsp_cd}, msg={rsp_msg})")
                self._positions.clear()
                self._account_summary.clear()
                self._notify_position_change()
                self._calculate_and_notify_account_pnl()
                self._last_errors.pop("positions", None)
                return

            if not _is_success_response(rsp_cd, rsp_msg):
                error_msg = f"[포지션 조회 실패] rsp_cd={rsp_cd}, msg={rsp_msg}"
                self._last_errors["positions"] = error_msg
                logger.error(f"[_fetch_positions] {error_msg}")
                return

            now = datetime.now()
            old_symbols = set(self._positions.keys())

            # 합산 정보 (OutBlock)
            if resp.cont_block:
                self._account_summary = {
                    "sunamt": resp.cont_block.sunamt,       # 추정순자산
                    "dtsunik": resp.cont_block.dtsunik,     # 실현손익
                    "mamt": resp.cont_block.mamt,           # 매입금액
                    "tappamt": resp.cont_block.tappamt,     # 평가금액
                    "tdtsunik": resp.cont_block.tdtsunik,   # 평가손익
                }

            # 종목별 잔고 (OutBlock1)
            self._positions.clear()

            if resp.block:
                for item in resp.block:
                    symbol = item.expcode
                    position = KrStockPositionItem(
                        symbol=symbol,
                        symbol_name=item.hname,
                        quantity=item.janqty,
                        sellable_quantity=item.mdposqt,
                        buy_price=item.pamt,
                        current_price=item.price,
                        buy_amount=item.mamt,
                        eval_amount=item.appamt,
                        pnl_amount=item.dtsunik,
                        pnl_rate=item.sunikrt,
                        market=item.marketgb,
                        last_updated=now,
                    )
                    self._positions[symbol] = position
                    self._current_prices[symbol] = item.price
            else:
                logger.info("[_fetch_positions] 보유종목 없음")

            # 구독 동기화
            new_symbols = set(self._positions.keys())
            if old_symbols != new_symbols and self._real_client:
                await self._sync_tick_subscriptions()

            self._notify_position_change()
            self._calculate_and_notify_account_pnl()
            self._last_errors.pop("positions", None)

        except Exception as e:
            error_msg = f"[포지션 조회 실패] {str(e)}"
            self._last_errors["positions"] = error_msg
            logger.error(f"[_fetch_positions] 조회 실패: {e}", exc_info=True)

    async def _fetch_balance(self):
        """예수금 조회 (CSPAQ22200)"""
        try:
            from ..accno.CSPAQ22200.blocks import CSPAQ22200InBlock1

            tr = self._accno_client.cspaq22200(
                body=CSPAQ22200InBlock1(BalCreTp="0"),
            )
            resp = await tr.req_async()

            rsp_cd = getattr(resp, 'rsp_cd', '')
            rsp_msg = getattr(resp, 'rsp_msg', '')

            if _is_no_data_response(rsp_cd, rsp_msg):
                logger.info(f"[_fetch_balance] 예수금 데이터 없음 (rsp_cd={rsp_cd})")
                self._last_errors.pop("balance", None)
                return

            if not _is_success_response(rsp_cd, rsp_msg):
                error_msg = f"[예수금 조회 실패] rsp_cd={rsp_cd}, msg={rsp_msg}"
                self._last_errors["balance"] = error_msg
                logger.error(f"[_fetch_balance] {error_msg}")
                return

            now = datetime.now()

            if resp.block2:
                b = resp.block2
                self._balance = KrStockBalanceInfo(
                    deposit=b.Dps,
                    d1_deposit=b.D1Dps,
                    d2_deposit=b.D2Dps,
                    orderable_amount=b.MnyOrdAbleAmt,
                    substitute_amount=b.SubstAmt,
                    margin_cash=b.MgnMny,
                    receivable_amount=b.RcvblAmt,
                    last_updated=now,
                )

            self._notify_balance_change()
            self._last_errors.pop("balance", None)

        except Exception as e:
            error_msg = f"[예수금 조회 실패] {str(e)}"
            self._last_errors["balance"] = error_msg
            logger.error(f"[_fetch_balance] 조회 실패: {e}", exc_info=True)

    async def _fetch_open_orders(self):
        """미체결 주문 조회 (t0425)"""
        try:
            from ..accno.t0425.blocks import T0425InBlock

            tr = self._accno_client.t0425(
                body=T0425InBlock(
                    chegb="2",    # 미체결만
                    medosu="0",   # 전체
                    sortgb="1",   # 역순
                ),
            )
            resp = await tr.req_async()

            rsp_cd = getattr(resp, 'rsp_cd', '')
            rsp_msg = getattr(resp, 'rsp_msg', '')

            if _is_no_data_response(rsp_cd, rsp_msg):
                logger.info(f"[_fetch_open_orders] 미체결 없음 (rsp_cd={rsp_cd})")
                self._open_orders.clear()
                self._notify_open_orders_change()
                self._last_errors.pop("open_orders", None)
                return

            if not _is_success_response(rsp_cd, rsp_msg):
                error_msg = f"[미체결 조회 실패] rsp_cd={rsp_cd}, msg={rsp_msg}"
                self._last_errors["open_orders"] = error_msg
                logger.error(f"[_fetch_open_orders] {error_msg}")
                return

            now = datetime.now()
            self._open_orders.clear()

            if resp.block:
                for item in resp.block:
                    order = KrStockOpenOrder(
                        order_no=item.ordno,
                        symbol=item.expcode,
                        order_type=item.medosu,
                        order_qty=item.qty,
                        order_price=item.price,
                        executed_qty=item.cheqty,
                        executed_price=item.cheprice,
                        remaining_qty=item.ordrem,
                        order_time=item.ordtime,
                        order_status=item.status,
                        order_method=item.hogagb,
                        last_updated=now,
                    )
                    self._open_orders[order.order_no] = order
            else:
                logger.info("[_fetch_open_orders] 미체결 주문 없음")

            self._notify_open_orders_change()
            self._last_errors.pop("open_orders", None)

        except Exception as e:
            error_msg = f"[미체결 조회 실패] {str(e)}"
            self._last_errors["open_orders"] = error_msg
            logger.error(f"[_fetch_open_orders] 조회 실패: {e}", exc_info=True)

    # ===== 실시간 구독 =====

    async def _setup_subscriptions(self):
        """실시간 구독 설정 (S3_/K3_ 틱, SC1 주문 이벤트)"""
        if not self._real_client:
            return

        await self._sync_tick_subscriptions()
        await self._setup_order_subscriptions()

    async def _sync_tick_subscriptions(self):
        """보유종목 틱 데이터 구독 동기화 (시장별 분리)"""
        if not self._real_client:
            return

        kospi_symbols: Set[str] = set()
        kosdaq_symbols: Set[str] = set()

        for symbol, pos in self._positions.items():
            if _is_kospi_market(pos.market):
                kospi_symbols.add(symbol)
            else:
                kosdaq_symbols.add(symbol)

        # S3_ (KOSPI) 구독 동기화
        s3 = self._real_client.S3_()
        await self._s3_subscription_manager.sync_subscriptions(
            kospi_symbols,
            subscribe_fn=lambda s: s3.add_s3__symbols([s]),
            unsubscribe_fn=lambda s: s3.remove_s3__symbols([s]),
        )
        s3.on_s3__message(self._on_tick_received)

        # K3_ (KOSDAQ) 구독 동기화
        k3 = self._real_client.K3_()
        await self._k3_subscription_manager.sync_subscriptions(
            kosdaq_symbols,
            subscribe_fn=lambda s: k3.add_k3__symbols([s]),
            unsubscribe_fn=lambda s: k3.remove_k3__symbols([s]),
        )
        k3.on_k3__message(self._on_tick_received)

    async def _setup_order_subscriptions(self):
        """주문 이벤트 구독 (SC1 주문체결)"""
        if not self._real_client:
            return

        try:
            sc1 = self._real_client.SC1()
            sc1.on_sc1_message(self._on_order_event)
        except Exception:
            pass

    async def _cleanup_subscriptions(self):
        """구독 해제"""
        if not self._real_client:
            return

        try:
            s3 = self._real_client.S3_()
            await self._s3_subscription_manager.clear_all(
                unsubscribe_fn=lambda s: s3.remove_s3__symbols([s])
            )
        except Exception:
            pass

        try:
            k3 = self._real_client.K3_()
            await self._k3_subscription_manager.clear_all(
                unsubscribe_fn=lambda s: k3.remove_k3__symbols([s])
            )
        except Exception:
            pass

    # ===== 실시간 이벤트 핸들러 =====

    def _on_tick_received(self, resp):
        """실시간 가격 수신 (S3_/K3_ 공통) -> 손익 재계산"""
        try:
            if not resp or not hasattr(resp, 'body') or not resp.body:
                return

            body = resp.body
            if not hasattr(body, 'shcode') or not hasattr(body, 'price'):
                return

            symbol = body.shcode  # 6자리 종목코드
            price = int(body.price)

            self._current_prices[symbol] = price

            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.eval_amount = price * pos.quantity
                pos.pnl_amount = pos.eval_amount - pos.buy_amount
                pos.last_updated = datetime.now()

                # 실시간 손익 계산 (수수료/세금 반영)
                pnl = self._calculator.calculate_realtime_pnl(
                    symbol=symbol,
                    quantity=pos.quantity,
                    buy_price=pos.buy_price,
                    current_price=price,
                    market=pos.market,
                )
                pos.realtime_pnl = pnl
                pos.pnl_rate = float(pnl.return_rate_percent)

                self._notify_position_change()
                self._calculate_and_notify_account_pnl()

        except Exception as e:
            print(f"[KrStockAccountTracker] 틱 처리 오류: {e}")

    def _on_order_event(self, resp):
        """SC1 주문체결 이벤트 수신 -> 체결 시 재조회"""
        try:
            if not resp or not hasattr(resp, 'body') or not resp.body:
                return

            order_type = getattr(resp.body, 'ordxctptncode', '')

            # 11: 체결, 12: 정정확인, 13: 취소확인
            if order_type in ('11', '12', '13'):
                self._schedule_coroutine(self._delayed_refresh())

        except Exception as e:
            print(f"[KrStockAccountTracker] 주문 이벤트 처리 오류: {e}")

    async def _delayed_refresh(self):
        """체결 후 지연 재조회"""
        await asyncio.sleep(self.DEFAULT_ORDER_DELAY)
        await self._fetch_all_data()

    async def _periodic_refresh(self):
        """주기적 갱신"""
        while self._is_running:
            await asyncio.sleep(self._refresh_interval)
            if self._is_running:
                await self._fetch_all_data()

    def _schedule_coroutine(self, coro):
        """스레드 안전하게 코루틴 스케줄링 (WebSocket 콜백 스레드 대응)"""
        try:
            asyncio.get_running_loop()
            asyncio.create_task(coro)
        except RuntimeError:
            # WebSocket 콜백 등 별도 스레드에서 호출 시
            loop = self._loop  # 로컬 복사로 TOCTOU 방지
            if loop is not None:
                try:
                    asyncio.run_coroutine_threadsafe(coro, loop)
                except RuntimeError:
                    pass  # loop already closed

    # ===== 계좌 수익률 계산 =====

    def _calculate_account_pnl(self) -> KrAccountPnLInfo:
        """전체 계좌 수익률 계산"""
        total_buy = 0
        total_eval = 0

        for pos in self._positions.values():
            total_buy += pos.buy_amount
            total_eval += pos.eval_amount

        total_pnl = total_eval - total_buy
        pnl_rate = (
            (Decimal(str(total_pnl)) / Decimal(str(total_buy)) * 100).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            if total_buy > 0
            else Decimal("0")
        )

        return KrAccountPnLInfo(
            account_pnl_rate=pnl_rate,
            total_eval_amount=total_eval,
            total_buy_amount=total_buy,
            total_pnl_amount=total_pnl,
            realized_pnl=self._account_summary.get("dtsunik", 0),
            estimated_asset=self._account_summary.get("sunamt", 0),
            position_count=len(self._positions),
            last_updated=datetime.now(),
        )

    def _calculate_and_notify_account_pnl(self):
        """계좌 수익률 계산 후 콜백 호출"""
        self._account_pnl = self._calculate_account_pnl()
        self._notify_account_pnl_change()

    # ===== 콜백 등록 =====

    def on_position_change(self, callback: Callable[[Dict[str, KrStockPositionItem]], Any]):
        """보유종목 변경 콜백 등록"""
        self._on_position_change_callbacks.append(callback)

    def on_balance_change(self, callback: Callable[[Optional[KrStockBalanceInfo]], Any]):
        """예수금 변경 콜백 등록"""
        self._on_balance_change_callbacks.append(callback)

    def on_open_orders_change(self, callback: Callable[[Dict[int, KrStockOpenOrder]], Any]):
        """미체결 주문 변경 콜백 등록"""
        self._on_open_orders_change_callbacks.append(callback)

    def on_account_pnl_change(self, callback: Callable[[KrAccountPnLInfo], Any]):
        """계좌 수익률 변경 콜백 등록"""
        self._on_account_pnl_change_callbacks.append(callback)

    def _notify_position_change(self):
        for callback in self._on_position_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    self._schedule_coroutine(callback(self._positions.copy()))
                else:
                    callback(self._positions.copy())
            except Exception:
                pass

    def _notify_balance_change(self):
        for callback in self._on_balance_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    self._schedule_coroutine(callback(self._balance))
                else:
                    callback(self._balance)
            except Exception:
                pass

    def _notify_open_orders_change(self):
        for callback in self._on_open_orders_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    self._schedule_coroutine(callback(self._open_orders.copy()))
                else:
                    callback(self._open_orders.copy())
            except Exception:
                pass

    def _notify_account_pnl_change(self):
        if self._account_pnl is None:
            return

        for callback in self._on_account_pnl_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    self._schedule_coroutine(callback(self._account_pnl))
                else:
                    callback(self._account_pnl)
            except Exception:
                pass

    # ===== 데이터 접근 API =====

    def get_positions(self) -> Dict[str, KrStockPositionItem]:
        """현재 보유종목 조회"""
        return self._positions.copy()

    def get_position(self, symbol: str) -> Optional[KrStockPositionItem]:
        """특정 종목 조회"""
        return self._positions.get(symbol)

    def get_balance(self) -> Optional[KrStockBalanceInfo]:
        """예수금 조회"""
        return self._balance

    def get_open_orders(self) -> Dict[int, KrStockOpenOrder]:
        """미체결 주문 조회"""
        return self._open_orders.copy()

    def get_account_pnl(self) -> Optional[KrAccountPnLInfo]:
        """현재 계좌 수익률 조회"""
        return self._account_pnl

    def get_last_errors(self) -> Dict[str, str]:
        """마지막 에러 상태 조회"""
        return self._last_errors.copy()

    def get_current_price(self, symbol: str) -> Optional[int]:
        """실시간 현재가 조회"""
        return self._current_prices.get(symbol)

    # ===== 수동 갱신 =====

    async def refresh_now(self):
        """수동 즉시 갱신"""
        await self._fetch_all_data()

    # ===== 설정 =====

    @property
    def commission_config(self) -> KrCommissionConfig:
        """현재 수수료/세금 설정"""
        return self._commission_config

    def update_commission_config(self, commission_rate: Optional[Decimal] = None):
        """수수료율 업데이트"""
        if commission_rate is not None:
            self._commission_config.commission_rate = commission_rate
            self._calculator.update_config(self._commission_config)

    @property
    def subscribed_symbols(self) -> Set[str]:
        """현재 틱 구독 중인 종목 (S3_ + K3_ 합산)"""
        return (
            self._s3_subscription_manager.subscribed_symbols
            | self._k3_subscription_manager.subscribed_symbols
        )

    @property
    def is_running(self) -> bool:
        """추적 실행 중 여부"""
        return self._is_running

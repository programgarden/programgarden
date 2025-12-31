"""
해외선물 계좌 추적기 (FuturesAccountTracker)

실시간 손익/예수금/미체결 주문을 추적합니다.
- o3121 API 기반 동적 종목 명세 관리
- 1분 주기 API 갱신
- 실시간 틱 데이터로 손익 계산
- 주문 체결 시 즉시 갱신
"""

from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import asyncio

from .models import (
    FuturesPositionItem,
    FuturesBalanceInfo,
    FuturesOpenOrder,
)
from .calculator import FuturesPnLCalculator, DEFAULT_FEE_PER_CONTRACT
from .symbol_spec_manager import SymbolSpecManager, SymbolSpec
from .subscription_manager import SubscriptionManager


class FuturesAccountTracker:
    """
    해외선물 계좌 추적기
    
    보유포지션, 예수금, 미체결 주문을 실시간으로 추적하고
    틱 데이터를 기반으로 손익을 계산합니다.
    """
    
    DEFAULT_REFRESH_INTERVAL = 60  # 1분
    DEFAULT_SPEC_REFRESH_HOURS = 6  # 6시간
    DEFAULT_ORDER_DELAY = 2  # 체결 후 재조회 대기 시간 (초)
    
    def __init__(
        self,
        accno_client,
        market_client,
        real_client=None,
        refresh_interval: int = DEFAULT_REFRESH_INTERVAL,
        spec_refresh_hours: int = DEFAULT_SPEC_REFRESH_HOURS,
        commission_rate: Decimal = DEFAULT_FEE_PER_CONTRACT,
    ):
        """
        Args:
            accno_client: 계좌 API 클라이언트 (overseas_futureoption().accno())
            market_client: 시세 API 클라이언트 (overseas_futureoption().market())
            real_client: 실시간 API 클라이언트 (overseas_futureoption().real()) - 필수
            refresh_interval: 주기적 갱신 간격 (초, 기본 60초)
            spec_refresh_hours: 종목 명세 갱신 주기 (시간, 기본 6시간)
            commission_rate: 계약당 수수료 ($, 기본 $7.5)
        """
        self._accno_client = accno_client
        self._market_client = market_client
        self._real_client = real_client
        self._refresh_interval = refresh_interval
        self._commission_rate = commission_rate
        
        # 종목 명세 관리자
        self._spec_manager = SymbolSpecManager(market_client, spec_refresh_hours)
        
        # 손익 계산기
        self._calculator = FuturesPnLCalculator(self._spec_manager, commission_rate)
        
        # 구독 관리자
        self._subscription_manager = SubscriptionManager()
        
        # 데이터 캐시
        self._positions: Dict[str, FuturesPositionItem] = {}
        self._balance: Optional[FuturesBalanceInfo] = None
        self._open_orders: Dict[str, FuturesOpenOrder] = {}
        self._current_prices: Dict[str, Decimal] = {}
        
        # 콜백
        self._on_position_change_callbacks: List[Callable] = []
        self._on_balance_change_callbacks: List[Callable] = []
        self._on_open_orders_change_callbacks: List[Callable] = []
        
        # Task 관리
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self):
        """추적 시작"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # 1. 종목 명세 초기화 (o3121 호출)
        await self._spec_manager.initialize()
        
        # 2. WebSocket 연결 (없으면 예외)
        if not self._real_client:
            raise ValueError(
                "real_client is required. "
                "Please provide real_client=overseas_futureoption().real() when creating tracker."
            )
        
        if not await self._real_client.is_connected():
                await self._real_client.connect()
        
        # 3. 초기 데이터 로드
        await self._fetch_all_data()
        
        # 4. 실시간 구독 설정
        await self._setup_subscriptions()
        
        # 5. 주기적 갱신 Task 시작
        self._refresh_task = asyncio.create_task(self._periodic_refresh())
    
    async def stop(self):
        """추적 중지"""
        self._is_running = False
        
        # 주기적 갱신 Task 취소
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
        
        # 종목 명세 갱신 중지
        await self._spec_manager.stop()
        
        # 구독 해제
        await self._cleanup_subscriptions()
    
    async def _fetch_all_data(self):
        """모든 데이터 조회 (보유포지션, 예수금, 미체결)"""
        # 보유포지션 조회 (CIDBQ01500)
        await self._fetch_positions()
        
        # 잠시 대기 (rate limit)
        await asyncio.sleep(1)
        
        # 예수금 조회 (CIDBQ03000)
        await self._fetch_balance()
        
        await asyncio.sleep(1)
        
        # 미체결 주문 조회 (CIDBQ01800)
        await self._fetch_open_orders()
    
    async def _fetch_positions(self):
        """보유포지션 조회 (CIDBQ01500)"""
        try:
            from ..accno.CIDBQ01500.blocks import CIDBQ01500InBlock1
            from datetime import datetime as dt
            
            tr = self._accno_client.CIDBQ01500(
                body=CIDBQ01500InBlock1(
                    RecCnt=1,
                    AcntTpCode="1",  # 위탁
                    QryDt=dt.now().strftime("%Y%m%d"),
                    BalTpCode="1",   # 합산
                    FcmAcntNo=""
                )
            )
            resp = await tr.req_async()
            
            # 00000: 실전 정상, 00136: 모의투자 정상, 00707: 모의투자 데이터없음
            if resp.rsp_cd in ("00000", "00136", "00707"):
                now = datetime.now()
                old_symbols = set(self._positions.keys())
                self._positions.clear()
                
                # block2에 보유포지션 데이터가 있음
                if hasattr(resp, 'block2') and resp.block2:
                    for item in resp.block2:
                        symbol = getattr(item, 'IsuCodeVal', '')
                        is_long = getattr(item, 'BnsTpCode', '2') == '2'  # 2: 매수
                        currency = getattr(item, 'CrcyCodeVal', 'USD')
                        
                        position = FuturesPositionItem(
                            symbol=symbol,
                            symbol_name=getattr(item, 'IsuNm', ''),
                            is_long=is_long,
                            quantity=int(getattr(item, 'BalQty', 0)),
                            entry_price=Decimal(str(getattr(item, 'PchsPrc', 0))),
                            current_price=Decimal(str(getattr(item, 'OvrsDrvtNowPrc', 0))),
                            pnl_amount=Decimal(str(getattr(item, 'AbrdFutsEvalPnlAmt', 0))),
                            opening_margin=Decimal(str(getattr(item, 'CsgnMgn', 0))),
                            maintenance_margin=Decimal(str(getattr(item, 'MaintMgn', 0))),
                            margin_call_rate=Decimal(str(getattr(item, 'MgnclRat', 0))),
                            currency=currency,
                            last_updated=now
                        )
                        
                        # 현재가 저장
                        self._current_prices[symbol] = position.current_price
                        
                        # 손익률 계산
                        if position.entry_price > 0:
                            position.pnl_rate = (
                                (position.current_price - position.entry_price) / position.entry_price * 100
                            )
                            if not is_long:
                                position.pnl_rate = -position.pnl_rate
                        
                        self._positions[symbol] = position
                
                # 구독 동기화
                new_symbols = set(self._positions.keys())
                if old_symbols != new_symbols and self._real_client:
                    await self._sync_tick_subscriptions()
                
                self._notify_position_change()
                
        except Exception as e:
            print(f"[FuturesAccountTracker] 보유포지션 조회 실패: {e}")
    
    async def _fetch_balance(self):
        """예수금/증거금 조회 (CIDBQ03000)"""
        try:
            from ..accno.CIDBQ03000.blocks import CIDBQ03000InBlock1
            
            tr = self._accno_client.CIDBQ03000(
                body=CIDBQ03000InBlock1(
                    RecCnt=1,
                    AcntTpCode="1",
                    TrdDt=""
                )
            )
            resp = await tr.req_async()
            
            # 성공: error_msg 없고 rsp_cd가 숫자로 시작
            if not resp.error_msg and resp.rsp_cd and resp.rsp_cd[0].isdigit():
                now = datetime.now()
                
                # block2에 통화별 예수금 데이터가 있음 (첫번째 USD 기준)
                if hasattr(resp, 'block2') and resp.block2:
                    # USD 데이터 찾기 (없으면 첫번째 사용)
                    item = None
                    for b in resp.block2:
                        if getattr(b, 'CrcyObjCode', '') == 'USD':
                            item = b
                            break
                    if item is None and resp.block2:
                        item = resp.block2[0]
                    
                    if item:
                        self._balance = FuturesBalanceInfo(
                            deposit=Decimal(str(getattr(item, 'OvrsFutsDps', 0))),
                            total_margin=Decimal(str(getattr(item, 'AbrdFutsCsgnMgn', 0))),
                            orderable_amount=Decimal(str(getattr(item, 'AbrdFutsOrdAbleAmt', 0))),
                            withdrawable_amount=Decimal(str(getattr(item, 'AbrdFutsWthdwAbleAmt', 0))),
                            pnl_amount=Decimal(str(getattr(item, 'AbrdFutsEvalPnlAmt', 0))),
                            realized_pnl=Decimal(str(getattr(item, 'AbrdFutsLqdtPnlAmt', 0))),
                            currency=getattr(item, 'CrcyObjCode', 'USD'),
                            last_updated=now
                        )
                        
                        self._notify_balance_change()
                
        except Exception as e:
            print(f"[FuturesAccountTracker] 예수금 조회 실패: {e}")
    
    async def _fetch_open_orders(self):
        """미체결 주문 조회 (CIDBQ01800)"""
        try:
            from ..accno.CIDBQ01800.blocks import CIDBQ01800InBlock1
            from datetime import datetime as dt
            
            tr = self._accno_client.CIDBQ01800(
                body=CIDBQ01800InBlock1(
                    RecCnt=1,
                    IsuCodeVal="",   # 전체 종목
                    OrdDt=dt.now().strftime("%Y%m%d"),
                    ThdayTpCode="",
                    OrdStatCode="2",  # 2: 미체결
                    BnsTpCode="0",    # 0: 전체
                    QryTpCode="1",    # 1: 역순
                    OrdPtnCode="00",  # 00: 전체
                    OvrsDrvtFnoTpCode="A"  # A: 전체
                )
            )
            resp = await tr.req_async()
            
            # 성공: error_msg 없고 rsp_cd가 숫자로 시작
            if not resp.error_msg and resp.rsp_cd and resp.rsp_cd[0].isdigit():
                now = datetime.now()
                self._open_orders.clear()
                
                # block2에 미체결 데이터가 있음
                if hasattr(resp, 'block2') and resp.block2:
                    for item in resp.block2:
                        order = FuturesOpenOrder(
                            order_no=str(getattr(item, 'OrdNo', '')),
                            symbol=getattr(item, 'IsuCodeVal', ''),
                            symbol_name=getattr(item, 'IsuNm', ''),
                            is_long=getattr(item, 'BnsTpCode', '2') == '2',
                            order_type=getattr(item, 'OrdPtnCode', ''),
                            order_qty=getattr(item, 'OrdQty', 0),
                            order_price=Decimal(str(getattr(item, 'OrdPrc', 0))),
                            executed_qty=getattr(item, 'ExecQty', 0),
                            remaining_qty=getattr(item, 'UnexecQty', 0),
                            order_time=getattr(item, 'OrdTime', ''),
                            order_status=getattr(item, 'OrdStatCode', ''),
                            last_updated=now
                        )
                        self._open_orders[order.order_no] = order
                
                self._notify_open_orders_change()
                
        except Exception as e:
            print(f"[FuturesAccountTracker] 미체결 조회 실패: {e}")
    
    async def _setup_subscriptions(self):
        """실시간 구독 설정 (OVC 틱, TC 주문 이벤트)"""
        if not self._real_client:
            return
        
        # OVC 틱 데이터 구독
        await self._sync_tick_subscriptions()
        
        # TC1/TC2 주문 이벤트 구독
        await self._setup_order_subscriptions()
    
    async def _sync_tick_subscriptions(self):
        """보유포지션 틱 데이터 구독 동기화"""
        if not self._real_client:
            return
        
        ovc = self._real_client.OVC()
        target_symbols = set(self._positions.keys())
        
        await self._subscription_manager.sync_subscriptions(
            target_symbols,
            subscribe_fn=lambda s: ovc.add_ovc_symbols([s]),
            unsubscribe_fn=lambda s: ovc.remove_ovc_symbols([s])
        )
        
        # 메시지 핸들러 등록
        ovc.on_ovc_message(self._on_tick_received)
    
    async def _setup_order_subscriptions(self):
        """주문 이벤트 구독 (TC1/TC2)"""
        if not self._real_client:
            return
        
        try:
            # TC2: 주문확인/거부
            tc2 = self._real_client.TC2()
            tc2.on_tc2_message(self._on_order_event)
        except Exception:
            pass
    
    async def _cleanup_subscriptions(self):
        """구독 해제"""
        if not self._real_client:
            return
        
        try:
            ovc = self._real_client.OVC()
            await self._subscription_manager.clear_all(
                unsubscribe_fn=lambda s: ovc.remove_ovc_symbols([s])
            )
        except Exception:
            pass
    
    def _on_tick_received(self, resp):
        """실시간 가격 수신 → 손익 재계산"""
        try:
            if not resp or not resp.body:
                return
            
            symbol = getattr(resp.body, 'symbol', None)
            curpr = getattr(resp.body, 'curpr', None)
            
            if not symbol or curpr is None:
                return
            
            price = Decimal(str(curpr))
            
            self._current_prices[symbol] = price
            
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.last_updated = datetime.now()
                
                # 실시간 손익 계산
                try:
                    pnl = self._calculator.calculate_realtime_pnl(
                        symbol=symbol,
                        quantity=pos.quantity,
                        entry_price=pos.entry_price,
                        current_price=price,
                        is_long=pos.is_long,
                        custom_fee_usd=self._commission_rate
                    )
                    pos.realtime_pnl = pnl
                    pos.pnl_amount = pnl.net_pl_usd
                    
                    # 손익률 계산
                    if pos.entry_price > 0:
                        pos.pnl_rate = (
                            (price - pos.entry_price) / pos.entry_price * 100
                        )
                        if not pos.is_long:
                            pos.pnl_rate = -pos.pnl_rate
                except Exception:
                    pass
                
                self._notify_position_change()
                
        except Exception as e:
            print(f"[FuturesAccountTracker] 틱 처리 오류: {e}")
    
    def _on_order_event(self, resp):
        """주문 이벤트 수신 → 체결 시 재조회"""
        try:
            # HO02: 체결확인
            service_id = getattr(resp.body, 'svcId', '')
            
            if service_id == 'HO02':
                asyncio.create_task(self._delayed_refresh())
                
        except Exception as e:
            print(f"[FuturesAccountTracker] 주문 이벤트 처리 오류: {e}")
    
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
    
    # ===== 콜백 등록 =====
    def on_position_change(self, callback: Callable[[Dict[str, FuturesPositionItem]], Any]):
        """보유포지션 변경 콜백 등록"""
        self._on_position_change_callbacks.append(callback)
    
    def on_balance_change(self, callback: Callable[[Optional[FuturesBalanceInfo]], Any]):
        """예수금 변경 콜백 등록"""
        self._on_balance_change_callbacks.append(callback)
    
    def on_open_orders_change(self, callback: Callable[[Dict[str, FuturesOpenOrder]], Any]):
        """미체결 주문 변경 콜백 등록"""
        self._on_open_orders_change_callbacks.append(callback)
    
    def _notify_position_change(self):
        """보유포지션 변경 알림"""
        for callback in self._on_position_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._positions.copy()))
                else:
                    callback(self._positions.copy())
            except Exception:
                pass
    
    def _notify_balance_change(self):
        """예수금 변경 알림"""
        for callback in self._on_balance_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._balance))
                else:
                    callback(self._balance)
            except Exception:
                pass
    
    def _notify_open_orders_change(self):
        """미체결 주문 변경 알림"""
        for callback in self._on_open_orders_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._open_orders.copy()))
                else:
                    callback(self._open_orders.copy())
            except Exception:
                pass
    
    # ===== 데이터 조회 =====
    def get_positions(self) -> Dict[str, FuturesPositionItem]:
        """현재 보유포지션 조회"""
        return self._positions.copy()
    
    def get_position(self, symbol: str) -> Optional[FuturesPositionItem]:
        """특정 종목 조회"""
        return self._positions.get(symbol)
    
    def get_balance(self) -> Optional[FuturesBalanceInfo]:
        """예수금/증거금 조회"""
        return self._balance
    
    def get_open_orders(self) -> Dict[str, FuturesOpenOrder]:
        """미체결 주문 조회"""
        return self._open_orders.copy()
    
    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """실시간 현재가 조회"""
        return self._current_prices.get(symbol)
    
    def get_symbol_spec(self, symbol: str) -> Optional[SymbolSpec]:
        """종목 명세 조회"""
        return self._spec_manager.get_spec(symbol)
    
    # ===== 수동 갱신 =====
    async def refresh_now(self):
        """수동 즉시 갱신"""
        await self._fetch_all_data()
    
    async def force_refresh_specs(self):
        """종목 명세 강제 갱신"""
        await self._spec_manager.force_refresh()
    
    # ===== 속성 =====
    @property
    def spec_manager(self) -> SymbolSpecManager:
        """종목 명세 관리자"""
        return self._spec_manager
    
    @property
    def available_symbols(self) -> List[str]:
        """사용 가능한 종목 목록"""
        return self._spec_manager.available_symbols
    
    @property
    def available_base_products(self) -> List[str]:
        """사용 가능한 기초상품 코드 목록"""
        return self._spec_manager.available_base_products
    
    @property
    def subscribed_symbols(self) -> Set[str]:
        """현재 틱 구독 중인 종목"""
        return self._subscription_manager.subscribed_symbols
    
    @property
    def is_running(self) -> bool:
        """추적 실행 중 여부"""
        return self._is_running
    
    @property
    def commission_rate(self) -> Decimal:
        """계약당 수수료"""
        return self._commission_rate
    
    def set_commission_rate(self, rate: Decimal):
        """계약당 수수료 설정"""
        self._commission_rate = rate
        self._calculator = FuturesPnLCalculator(self._spec_manager, rate)

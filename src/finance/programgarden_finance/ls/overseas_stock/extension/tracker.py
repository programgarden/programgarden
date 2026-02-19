"""
해외주식 계좌 추적기 (StockAccountTracker)

실시간 손익/예수금/미체결 주문을 추적합니다.
- 1분 주기 API 갱신
- 실시간 틱 데이터로 손익 계산
- 주문 체결 시 즉시 갱신
- WebSocket 공유 및 중복 방지
- 계좌 전체 수익률 계산 및 콜백 지원
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import asyncio

from .models import (
    StockPositionItem,
    StockBalanceInfo,
    StockOpenOrder,
    CommissionConfig,
    AccountPnLInfo,
)
from .calculator import StockPnLCalculator
from .subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

# LS증권 API 응답 코드
SUCCESS_CODES = {"00000", "00001"}  # 정상 응답

# "데이터 없음" 판단 패턴 (rsp_msg에서 확인)
NO_DATA_PATTERNS = ["없습니다", "없음", "no data", "not found", "조회내역"]


def is_no_data_response(rsp_cd: str, rsp_msg: str) -> bool:
    """응답이 '데이터 없음' 케이스인지 판단"""
    # 성공 코드가 아니고, 메시지에 "없음" 패턴이 있으면 데이터 없음
    if rsp_cd in SUCCESS_CODES:
        return False
    msg_lower = (rsp_msg or "").lower()
    return any(pattern in msg_lower for pattern in NO_DATA_PATTERNS)


class StockAccountTracker:
    """
    해외주식 계좌 추적기
    
    보유종목, 예수금, 미체결 주문을 실시간으로 추적하고
    틱 데이터를 기반으로 손익을 계산합니다.
    """
    
    DEFAULT_REFRESH_INTERVAL = 60  # 1분
    DEFAULT_ORDER_DELAY = 3  # 체결 후 재조회 대기 시간 (초)
    
    def __init__(
        self,
        accno_client,
        real_client=None,
        refresh_interval: int = DEFAULT_REFRESH_INTERVAL,
        commission_rates: Optional[Dict[str, Decimal]] = None,
        tax_rates: Optional[Dict[str, Decimal]] = None,
    ):
        """
        Args:
            accno_client: 계좌 API 클라이언트 (overseas_stock().accno())
            real_client: 실시간 API 클라이언트 (overseas_stock().real()) - 필수
            refresh_interval: 주기적 갱신 간격 (초, 기본 60초)
            commission_rates: 통화별 수수료율 (예: {"USD": 0.0025})
            tax_rates: 통화별 거래세율 (예: {"HK": 0.001})
        """
        self._accno_client = accno_client
        self._real_client = real_client
        self._refresh_interval = refresh_interval
        
        # 수수료/세금 설정
        comm_rates = commission_rates or {"DEFAULT": Decimal("0.0025")}
        t_rates = tax_rates or {"DEFAULT": Decimal("0")}
        self._commission_config = CommissionConfig(
            commission_rates=comm_rates,
            tax_rates=t_rates
        )
        
        # 손익 계산기
        self._calculator = StockPnLCalculator(self._commission_config)
        
        # 구독 관리자
        self._subscription_manager = SubscriptionManager()
        
        # 데이터 캐시
        self._positions: Dict[str, StockPositionItem] = {}
        self._balances: Dict[str, StockBalanceInfo] = {}
        self._open_orders: Dict[str, StockOpenOrder] = {}
        self._current_prices: Dict[str, Decimal] = {}
        
        # 계좌 수익률 캐시
        self._account_pnl: Optional[AccountPnLInfo] = None
        
        # 콜백
        self._on_position_change_callbacks: List[Callable] = []
        self._on_balance_change_callbacks: List[Callable] = []
        self._on_open_orders_change_callbacks: List[Callable] = []
        self._on_account_pnl_change_callbacks: List[Callable] = []  # 계좌 수익률 콜백
        
        # Task 관리
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # 에러 상태 저장 (서버 오류 등)
        self._last_errors: Dict[str, str] = {}
    
    async def start(self):
        """추적 시작"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # 1. WebSocket 연결 (없으면 예외)
        if not self._real_client:
            raise ValueError(
                "real_client is required. "
                "Please provide real_client=overseas_stock().real() when creating tracker."
            )
        
        # 외부 WebSocket 연결 상태 확인
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
        
        # 주기적 갱신 Task 취소
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
        
        # 구독 해제
        await self._cleanup_subscriptions()
    
    async def _fetch_all_data(self):
        """모든 데이터 조회 (보유종목, 예수금, 미체결)"""
        # 보유종목 조회 (COSOQ00201)
        await self._fetch_positions()
        
        # 잠시 대기 (rate limit)
        await asyncio.sleep(2)
        
        # 미체결 주문 조회 (COSAQ00102)
        await self._fetch_open_orders()
    
    async def _fetch_positions(self):
        """보유종목 조회 (COSOQ00201)"""
        try:
            from ..accno.COSOQ00201.blocks import COSOQ00201InBlock1
            from datetime import datetime as dt
            
            tr = self._accno_client.cosoq00201(
                body=COSOQ00201InBlock1(
                    RecCnt=1,
                    BaseDt=dt.now().strftime("%Y%m%d"),
                    CrcyCode="ALL",
                    AstkBalTpCode="00"
                ),
            )
            resp = await tr.req_async()
            
            # 응답 코드 확인
            rsp_cd = getattr(resp, 'rsp_cd', '')
            rsp_msg = getattr(resp, 'rsp_msg', '')
            
            # "데이터 없음" 응답 → 정상 케이스 (빈 데이터)
            if is_no_data_response(rsp_cd, rsp_msg):
                logger.info(f"[_fetch_positions] 보유종목 없음 (rsp_cd={rsp_cd}, msg={rsp_msg})")
                self._positions.clear()
                self._balances.clear()
                self._notify_position_change()
                self._notify_balance_change()
                self._calculate_and_notify_account_pnl()  # 계좌 수익률 갱신
                self._last_errors.pop("positions", None)
                return
            
            # 성공이 아닌 다른 응답 → 에러
            if rsp_cd and rsp_cd not in SUCCESS_CODES:
                error_msg = f"[포지션 조회 실패] rsp_cd={rsp_cd}, msg={rsp_msg}"
                self._last_errors["positions"] = error_msg
                logger.error(f"[_fetch_positions] {error_msg}")
                return
            
            # block 데이터 처리 (block이 비어있으면 보유종목 없음 = 정상 케이스)
            now = datetime.now()
            
            # 통화별 잔고 (OutBlock3)
            self._balances.clear()
            if hasattr(resp, 'block3') and resp.block3:
                for item in resp.block3:
                    balance = StockBalanceInfo(
                        currency_code=item.CrcyCode,
                        deposit=Decimal(str(item.FcurrDps)),
                        orderable_amount=Decimal(str(item.FcurrOrdAbleAmt)),
                        eval_amount=Decimal(str(item.FcurrEvalAmt)),
                        pnl_amount=Decimal(str(item.FcurrEvalPnlAmt)),
                        pnl_rate=Decimal(str(item.PnlRat)),
                        exchange_rate=Decimal(str(item.BaseXchrat)),
                        deposit_krw=Decimal(str(item.DpsConvEvalAmt)),
                        last_updated=now
                    )
                    self._balances[item.CrcyCode] = balance
            
            # 종목별 잔고 (OutBlock4)
            old_symbols = set(self._positions.keys())
            self._positions.clear()
            
            if hasattr(resp, 'block4') and resp.block4:
                for item in resp.block4:
                    symbol = item.ShtnIsuNo  # 단축종목번호 (예: SOXL)
                    position = StockPositionItem(
                        symbol=symbol,
                        symbol_name=item.JpnMktHanglIsuNm or symbol,
                        currency_code=item.CrcyCode,
                        quantity=item.AstkBalQty,
                        sellable_quantity=item.AstkSellAbleQty,
                        buy_price=Decimal(str(item.FcstckUprc)),
                        current_price=Decimal(str(item.OvrsScrtsCurpri)),
                        buy_amount=Decimal(str(item.FcurrBuyAmt)),
                        eval_amount=Decimal(str(item.FcurrEvalAmt)),
                        pnl_amount=Decimal(str(item.FcurrEvalPnlAmt)),
                        pnl_rate=Decimal(str(item.PnlRat)),
                        exchange_rate=Decimal(str(item.BaseXchrat)),
                        market_code=item.FcurrMktCode,
                        last_updated=now
                    )
                    self._positions[symbol] = position
                    self._current_prices[symbol] = position.current_price
            else:
                logger.info("[_fetch_positions] 보유종목 없음")
            
            # 구독 동기화 (종목 변경 시)
            new_symbols = set(self._positions.keys())
            if old_symbols != new_symbols and self._real_client:
                await self._sync_tick_subscriptions()
            
            # 콜백 호출
            self._notify_position_change()
            self._notify_balance_change()
            self._calculate_and_notify_account_pnl()  # 계좌 수익률 갱신
            
            # 성공 시 에러 상태 클리어
            self._last_errors.pop("positions", None)
                
        except Exception as e:
            error_msg = f"[포지션 조회 실패] {str(e)}"
            self._last_errors["positions"] = error_msg
            logger.error(f"[_fetch_positions] 조회 실패: {e}", exc_info=True)
    
    async def _fetch_open_orders(self):
        """미체결 주문 조회 (COSAQ00102)"""
        try:
            from ..accno.COSAQ00102.blocks import COSAQ00102InBlock1
            from datetime import datetime as dt
            
            tr = self._accno_client.cosaq00102(
                body=COSAQ00102InBlock1(
                    RecCnt=1,
                    QryTpCode="1",
                    BkseqTpCode="1",
                    OrdMktCode="00",  # 전체
                    BnsTpCode="0",    # 전체
                    IsuNo="",
                    SrtOrdNo=999999999,
                    OrdDt=dt.now().strftime("%Y%m%d"),
                    ExecYn="2",       # 2: 미체결
                    CrcyCode="000",   # 전체
                    ThdayBnsAppYn="0",
                    LoanBalHldYn="0"
                ),
            )
            resp = await tr.req_async()
            
            # 응답 코드 확인
            rsp_cd = getattr(resp, 'rsp_cd', '')
            rsp_msg = getattr(resp, 'rsp_msg', '')
            
            # "데이터 없음" 응답 → 정상 케이스 (빈 데이터)
            if is_no_data_response(rsp_cd, rsp_msg):
                logger.info(f"[_fetch_open_orders] 미체결 주문 없음 (rsp_cd={rsp_cd}, msg={rsp_msg})")
                self._open_orders.clear()
                self._notify_open_orders_change()
                self._last_errors.pop("open_orders", None)
                return
            
            # 성공이 아닌 다른 응답 → 에러
            if rsp_cd and rsp_cd not in SUCCESS_CODES:
                error_msg = f"[미체결 조회 실패] rsp_cd={rsp_cd}, msg={rsp_msg}"
                self._last_errors["open_orders"] = error_msg
                logger.error(f"[_fetch_open_orders] {error_msg}")
                return
            
            # block 데이터 처리 (block이 비어있으면 미체결 없음 = 정상 케이스)
            now = datetime.now()
            self._open_orders.clear()
            
            if hasattr(resp, 'block1') and resp.block1:
                for item in resp.block1:
                    order = StockOpenOrder(
                        order_no=getattr(item, 'OrdNo', ''),
                        symbol=getattr(item, 'IsuNo', ''),
                        symbol_name=getattr(item, 'IsuNm', ''),
                        order_type=getattr(item, 'OrdPtnCode', ''),
                        order_qty=getattr(item, 'OrdQty', 0),
                        order_price=Decimal(str(getattr(item, 'OrdPrc', 0))),
                        executed_qty=getattr(item, 'ExecQty', 0),
                        remaining_qty=getattr(item, 'UnexecQty', 0),
                        order_time=getattr(item, 'OrdTime', ''),
                        order_status=getattr(item, 'OrdStatCode', ''),
                        currency_code=getattr(item, 'CrcyCode', 'USD'),
                        last_updated=now
                    )
                    self._open_orders[order.order_no] = order
            else:
                logger.info("[_fetch_open_orders] 미체결 주문 없음")
            
            self._notify_open_orders_change()
            
            # 성공 시 에러 상태 클리어
            self._last_errors.pop("open_orders", None)
                
        except Exception as e:
            error_msg = f"[미체결 조회 실패] {str(e)}"
            self._last_errors["open_orders"] = error_msg
            logger.error(f"[_fetch_open_orders] 조회 실패: {e}", exc_info=True)
    
    async def _setup_subscriptions(self):
        """실시간 구독 설정 (GSC 틱, AS 주문 이벤트)"""
        if not self._real_client:
            return
        
        # GSC 틱 데이터 구독
        await self._sync_tick_subscriptions()
        
        # AS0~AS3 주문 이벤트 구독
        await self._setup_order_subscriptions()
    
    async def _sync_tick_subscriptions(self):
        """보유종목 틱 데이터 구독 동기화"""
        if not self._real_client:
            return
        
        gsc = self._real_client.GSC()
        target_symbols = set(self._positions.keys())
        
        # 시장코드 prefix 추가 (예: SOXL -> 81SOXL)
        prefixed_symbols = set()
        for symbol in target_symbols:
            pos = self._positions.get(symbol)
            if pos and pos.market_code:
                prefixed_symbols.add(f"{pos.market_code}{symbol}")
            else:
                prefixed_symbols.add(f"81{symbol}")  # 기본값 뉴욕
        
        await self._subscription_manager.sync_subscriptions(
            prefixed_symbols,
            subscribe_fn=lambda s: gsc.add_gsc_symbols([s]),
            unsubscribe_fn=lambda s: gsc.remove_gsc_symbols([s])
        )
        
        # 메시지 핸들러 등록
        gsc.on_gsc_message(self._on_tick_received)
    
    async def _setup_order_subscriptions(self):
        """주문 이벤트 구독 (AS0~AS3)"""
        if not self._real_client:
            return
        
        try:
            # AS0: 주문 접수/체결
            as0 = self._real_client.AS0()
            as0.on_as0_message(self._on_order_event)
        except Exception:
            pass
    
    async def _cleanup_subscriptions(self):
        """구독 해제"""
        if not self._real_client:
            return
        
        try:
            gsc = self._real_client.GSC()
            await self._subscription_manager.clear_all(
                unsubscribe_fn=lambda s: gsc.remove_gsc_symbols([s])
            )
        except Exception:
            pass
    
    def _on_tick_received(self, resp):
        """실시간 가격 수신 → 손익 재계산"""
        try:
            # resp 또는 body가 None인 경우 무시
            if not resp or not hasattr(resp, 'body') or not resp.body:
                return
            
            body = resp.body
            if not hasattr(body, 'symbol') or not hasattr(body, 'price'):
                return
            
            symbol_raw = body.symbol  # 예: 81SOXL
            price = Decimal(str(body.price))
            
            # prefix 제거
            symbol = symbol_raw[2:] if len(symbol_raw) > 2 else symbol_raw
            
            self._current_prices[symbol] = price
            
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.last_updated = datetime.now()
                
                # 실시간 손익 계산
                pnl = self._calculator.calculate_realtime_pnl(
                    symbol=symbol,
                    quantity=pos.quantity,
                    buy_price=pos.buy_price,
                    current_price=price,
                    currency=pos.currency_code,
                    exchange_rate=pos.exchange_rate if pos.exchange_rate > 0 else None
                )
                pos.realtime_pnl = pnl
                pos.pnl_amount = pnl.net_profit_foreign
                pos.pnl_rate = pnl.return_rate_percent
                pos.eval_amount = price * pos.quantity
                
                self._notify_position_change()
                self._calculate_and_notify_account_pnl()  # 틱마다 계좌 수익률 갱신
                
        except Exception as e:
            print(f"[StockAccountTracker] 틱 처리 오류: {e}")
    
    def _on_order_event(self, resp):
        """주문 이벤트 수신 → 체결 시 재조회"""
        try:
            # 체결 완료 여부 확인
            order_type = getattr(resp.body, 'sOrdxctPtnCode', '')
            
            # 14: 신규체결, 12: 정정완료, 13: 취소완료
            if order_type in ('14', '12', '13'):
                # 비동기로 재조회 (체결 후 잠시 대기)
                asyncio.create_task(self._delayed_refresh())
                
        except Exception as e:
            print(f"[StockAccountTracker] 주문 이벤트 처리 오류: {e}")
    
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
    
    # ===== 계좌 수익률 계산 =====
    def _calculate_account_pnl(self) -> AccountPnLInfo:
        """전체 계좌 수익률 계산 (총 평가손익 / 총 매입금액)"""
        total_buy = Decimal("0")
        total_eval = Decimal("0")
        
        for pos in self._positions.values():
            total_buy += pos.buy_amount
            total_eval += pos.eval_amount
        
        total_pnl = total_eval - total_buy
        pnl_rate = (total_pnl / total_buy * 100) if total_buy > 0 else Decimal("0")
        
        return AccountPnLInfo(
            account_pnl_rate=pnl_rate,
            total_eval_amount=total_eval,
            total_buy_amount=total_buy,
            total_pnl_amount=total_pnl,
            position_count=len(self._positions),
            currency="USD",  # 기본 통화
            last_updated=datetime.now(),
        )
    
    def _calculate_and_notify_account_pnl(self):
        """계좌 수익률 계산 후 콜백 호출"""
        self._account_pnl = self._calculate_account_pnl()
        self._notify_account_pnl_change()
    
    # ===== 콜백 등록 =====
    def on_position_change(self, callback: Callable[[Dict[str, StockPositionItem]], Any]):
        """보유종목 변경 콜백 등록"""
        self._on_position_change_callbacks.append(callback)
    
    def on_balance_change(self, callback: Callable[[Dict[str, StockBalanceInfo]], Any]):
        """예수금 변경 콜백 등록"""
        self._on_balance_change_callbacks.append(callback)
    
    def on_open_orders_change(self, callback: Callable[[Dict[str, StockOpenOrder]], Any]):
        """미체결 주문 변경 콜백 등록"""
        self._on_open_orders_change_callbacks.append(callback)
    
    def on_account_pnl_change(self, callback: Callable[[AccountPnLInfo], Any]):
        """계좌 수익률 변경 콜백 등록
        
        틱 수신마다 호출됩니다. 필요시 서버에서 쓰로틀링하세요.
        
        Args:
            callback: AccountPnLInfo를 인자로 받는 콜백 함수
        
        Example:
            tracker.on_account_pnl_change(lambda pnl: print(f"계좌 수익률: {pnl.account_pnl_rate:.2f}%"))
        """
        self._on_account_pnl_change_callbacks.append(callback)
    
    def _notify_position_change(self):
        """보유종목 변경 알림"""
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
                    asyncio.create_task(callback(self._balances.copy()))
                else:
                    callback(self._balances.copy())
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
    
    def _notify_account_pnl_change(self):
        """계좌 수익률 변경 알림"""
        if self._account_pnl is None:
            return
        
        for callback in self._on_account_pnl_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self._account_pnl))
                else:
                    callback(self._account_pnl)
            except Exception:
                pass
    
    # ===== 데이터 조회 =====
    def get_positions(self) -> Dict[str, StockPositionItem]:
        """현재 보유종목 조회"""
        return self._positions.copy()
    
    def get_position(self, symbol: str) -> Optional[StockPositionItem]:
        """특정 종목 조회"""
        return self._positions.get(symbol)
    
    def get_balances(self) -> Dict[str, StockBalanceInfo]:
        """통화별 예수금 조회"""
        return self._balances.copy()
    
    def get_balance(self, currency: str = "USD") -> Optional[StockBalanceInfo]:
        """특정 통화 예수금 조회"""
        return self._balances.get(currency)
    
    def get_open_orders(self) -> Dict[str, StockOpenOrder]:
        """미체결 주문 조회"""
        return self._open_orders.copy()
    
    def get_account_pnl(self) -> Optional[AccountPnLInfo]:
        """현재 계좌 수익률 조회"""
        return self._account_pnl
    
    def get_last_errors(self) -> Dict[str, str]:
        """마지막 에러 상태 조회
        
        Returns:
            Dict[str, str]: 키별 에러 메시지
                - "positions": 포지션 조회 에러
                - "open_orders": 미체결 조회 에러
        """
        return self._last_errors.copy()
    
    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """실시간 현재가 조회"""
        return self._current_prices.get(symbol)
    
    # ===== 수동 갱신 =====
    async def refresh_now(self):
        """수동 즉시 갱신"""
        await self._fetch_all_data()
    
    # ===== 설정 =====
    @property
    def commission_config(self) -> CommissionConfig:
        """현재 수수료/세금 설정"""
        return self._commission_config
    
    def update_commission_config(
        self,
        commission_rates: Optional[Dict[str, Decimal]] = None,
        tax_rates: Optional[Dict[str, Decimal]] = None
    ):
        """수수료/세금 설정 업데이트"""
        if commission_rates:
            self._commission_config.commission_rates.update(commission_rates)
        if tax_rates:
            self._commission_config.tax_rates.update(tax_rates)
        self._calculator.update_config(self._commission_config)
    
    @property
    def subscribed_symbols(self) -> Set[str]:
        """현재 틱 구독 중인 종목"""
        return self._subscription_manager.subscribed_symbols
    
    @property
    def is_running(self) -> bool:
        """추적 실행 중 여부"""
        return self._is_running

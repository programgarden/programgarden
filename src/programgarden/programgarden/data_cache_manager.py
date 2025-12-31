"""Data caching layer for Programgarden trading systems.

EN:
    Provides centralized caching for market data, account positions, balances,
    and open orders. Integrates with finance package Trackers for real-time
    updates with periodic refresh.

KR:
    시장 데이터, 계좌 포지션, 예수금, 미체결 주문을 위한 중앙 캐싱 레이어입니다.
    finance 패키지의 Tracker와 통합하여 실시간 업데이트와 주기적 갱신을 제공합니다.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from programgarden_finance import LS

logger = logging.getLogger("programgarden.data_cache_manager")


class MarketDataCache:
    """시장 종목 데이터 캐시 (1시간 TTL)"""
    
    DEFAULT_TTL_SECONDS = 3600  # 1시간
    
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._ttl = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._fetch_functions: Dict[str, Callable] = {}
    
    def is_expired(self, key: str) -> bool:
        """캐시 만료 여부 확인"""
        if key not in self._timestamps:
            return True
        return datetime.now() - self._timestamps[key] > timedelta(seconds=self._ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """캐시된 데이터 조회 (만료 시 None)"""
        if self.is_expired(key):
            return None
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """캐시에 데이터 저장"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
    
    def register_fetch_function(self, key: str, fetch_fn: Callable) -> None:
        """캐시 갱신용 fetch 함수 등록"""
        self._fetch_functions[key] = fetch_fn
    
    async def get_or_fetch(self, key: str, fetch_fn: Optional[Callable] = None) -> Any:
        """캐시 조회, 없거나 만료 시 fetch"""
        cached = self.get(key)
        if cached is not None:
            return cached
        
        fn = fetch_fn or self._fetch_functions.get(key)
        if fn:
            try:
                data = await fn() if asyncio.iscoroutinefunction(fn) else fn()
                self.set(key, data)
                return data
            except Exception as e:
                logger.warning(f"캐시 fetch 실패 ({key}): {e}")
                return self._cache.get(key)  # 실패 시 이전 캐시 반환
        return None
    
    async def start_background_refresh(self) -> None:
        """백그라운드 갱신 시작"""
        if self._is_running:
            return
        self._is_running = True
        self._refresh_task = asyncio.create_task(self._periodic_refresh())
    
    async def stop_background_refresh(self) -> None:
        """백그라운드 갱신 중지"""
        self._is_running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
    
    async def _periodic_refresh(self) -> None:
        """주기적 갱신 (TTL 기준)"""
        while self._is_running:
            await asyncio.sleep(self._ttl)
            if not self._is_running:
                break
            for key, fetch_fn in self._fetch_functions.items():
                try:
                    data = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
                    self.set(key, data)
                    logger.debug(f"캐시 갱신 완료: {key}")
                except Exception as e:
                    logger.warning(f"캐시 갱신 실패 ({key}): {e}")
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        self._cache.clear()
        self._timestamps.clear()


class AccountTracker:
    """계좌 추적기 래퍼 (주식/선물 통합)"""
    
    def __init__(self, product: str = "overseas_stock"):
        self._product = product
        self._tracker = None
        self._is_initialized = False
    
    async def initialize(self, ls: LS, paper_trading: bool = False) -> bool:
        """Tracker 초기화"""
        try:
            if self._product == "overseas_stock":
                accno = ls.overseas_stock().accno()
                real = ls.overseas_stock().real()
                await real.connect()
                self._tracker = accno.account_tracker(real_client=real)
            elif self._product == "overseas_futures":
                accno = ls.overseas_futureoption().accno()
                market = ls.overseas_futureoption().market()
                real = ls.overseas_futureoption().real()
                await real.connect()
                # 해외선물은 market_client 필수 (o3121 종목 명세 조회용)
                self._tracker = accno.account_tracker(
                    market_client=market,
                    real_client=real
                )
            else:
                logger.error(f"지원하지 않는 상품: {self._product}")
                return False
            
            await self._tracker.start()
            self._is_initialized = True
            logger.info(f"AccountTracker 초기화 완료: {self._product}")
            return True
        except Exception as e:
            logger.error(f"AccountTracker 초기화 실패: {e}")
            return False
    
    async def stop(self) -> None:
        """Tracker 중지"""
        if self._tracker:
            await self._tracker.stop()
            self._is_initialized = False
            logger.info(f"AccountTracker 중지: {self._product}")
    
    @property
    def is_ready(self) -> bool:
        """Tracker 준비 상태"""
        return self._is_initialized and self._tracker is not None
    
    def get_positions(self) -> Dict[str, Any]:
        """보유종목 조회"""
        if not self.is_ready:
            return {}
        return self._tracker.get_positions()
    
    def get_balances(self) -> Dict[str, Any]:
        """예수금 조회 (주식: 통화별 Dict, 선물: 단일 객체를 Dict로 래핑)"""
        if not self.is_ready:
            return {}
        # 해외선물은 get_balance() (단일), 해외주식은 get_balances() (Dict)
        if self._product == "overseas_futures":
            balance = self._tracker.get_balance()
            return {"USD": balance} if balance else {}
        return self._tracker.get_balances()
    
    def get_open_orders(self) -> Dict[str, Any]:
        """미체결 주문 조회"""
        if not self.is_ready:
            return {}
        return self._tracker.get_open_orders()
    
    def get_current_price(self, symbol: str) -> Optional[Any]:
        """현재가 조회"""
        if not self.is_ready:
            return None
        return self._tracker.get_current_price(symbol)
    
    async def refresh_now(self) -> None:
        """즉시 갱신"""
        if self.is_ready:
            await self._tracker.refresh_now()
    
    def on_position_change(self, callback: Callable) -> None:
        """보유종목 변경 콜백"""
        if self._tracker:
            self._tracker.on_position_change(callback)
    
    def on_balance_change(self, callback: Callable) -> None:
        """예수금 변경 콜백"""
        if self._tracker:
            self._tracker.on_balance_change(callback)
    
    def on_open_orders_change(self, callback: Callable) -> None:
        """미체결 변경 콜백"""
        if self._tracker:
            self._tracker.on_open_orders_change(callback)


class DataCacheManager:
    """통합 데이터 캐시 매니저"""
    
    def __init__(self):
        self._market_cache = MarketDataCache()
        self._account_tracker: Optional[AccountTracker] = None
        self._product: Optional[str] = None
        self._is_initialized = False
    
    async def initialize(
        self,
        ls: LS,
        product: str = "overseas_stock",
        paper_trading: bool = False
    ) -> bool:
        """캐시 매니저 초기화
        
        Raises:
            RuntimeError: AccountTracker 초기화 실패 시
        """
        self._product = product
        
        # AccountTracker 초기화
        self._account_tracker = AccountTracker(product=product)
        tracker_ok = await self._account_tracker.initialize(ls, paper_trading)
        
        if not tracker_ok:
            self._account_tracker = None
            raise RuntimeError(
                f"AccountTracker 초기화에 실패했습니다. "
                f"product={product}, paper_trading={paper_trading}"
            )
        
        # 시장 데이터 캐시 시작
        await self._market_cache.start_background_refresh()
        
        self._is_initialized = True
        return True
    
    async def stop(self) -> None:
        """캐시 매니저 중지"""
        if self._account_tracker:
            await self._account_tracker.stop()
        await self._market_cache.stop_background_refresh()
        self._is_initialized = False
    
    @property
    def market_cache(self) -> MarketDataCache:
        """시장 데이터 캐시"""
        return self._market_cache
    
    @property
    def account_tracker(self) -> Optional[AccountTracker]:
        """계좌 추적기"""
        return self._account_tracker
    
    @property
    def has_tracker(self) -> bool:
        """Tracker 사용 가능 여부"""
        return self._account_tracker is not None and self._account_tracker.is_ready
    
    def get_positions(self) -> Dict[str, Any]:
        """보유종목 조회 (Tracker 우선)"""
        if self.has_tracker:
            return self._account_tracker.get_positions()
        return {}
    
    def get_balances(self) -> Dict[str, Any]:
        """예수금 조회 (Tracker 우선)"""
        if self.has_tracker:
            return self._account_tracker.get_balances()
        return {}
    
    def get_open_orders(self) -> Dict[str, Any]:
        """미체결 조회 (Tracker 우선)"""
        if self.has_tracker:
            return self._account_tracker.get_open_orders()
        return {}
    
    async def get_market_symbols(self, fetch_fn: Callable) -> List[Any]:
        """시장 종목 조회 (캐시 우선)"""
        key = f"market_symbols_{self._product}"
        self._market_cache.register_fetch_function(key, fetch_fn)
        return await self._market_cache.get_or_fetch(key, fetch_fn) or []
    
    async def get_cached_data(
        self,
        product: str,
        data_type: str,
        fetch_fn: Callable
    ) -> Any:
        """캐시된 데이터 조회 (범용 캐시 메서드)
        
        EN:
            Generic cache retrieval with automatic fetch on miss or expiry.
            Used for deposit (dps), market data, etc.
        
        KR:
            캐시 미스 또는 만료 시 자동 fetch하는 범용 캐시 조회.
            예수금(dps), 시장 데이터 등에 사용.
        
        Parameters:
            product (str): 상품 유형 (overseas_stock, overseas_futures)
            data_type (str): 데이터 타입 (dps, market_data 등)
            fetch_fn (Callable): 캐시 미스 시 호출할 fetch 함수
            
        Returns:
            Any: 캐시된 또는 새로 fetch한 데이터
        """
        key = f"{product}_{data_type}"
        return await self._market_cache.get_or_fetch(key, fetch_fn)
    
    async def refresh_account_data(self) -> None:
        """계좌 데이터 즉시 갱신"""
        if self.has_tracker:
            await self._account_tracker.refresh_now()


# 싱글톤 인스턴스
_cache_manager_instance: Optional[DataCacheManager] = None


def get_cache_manager() -> DataCacheManager:
    """캐시 매니저 싱글톤 인스턴스 반환"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = DataCacheManager()
    return _cache_manager_instance


def reset_cache_manager() -> None:
    """캐시 매니저 초기화 (테스트용)"""
    global _cache_manager_instance
    _cache_manager_instance = None

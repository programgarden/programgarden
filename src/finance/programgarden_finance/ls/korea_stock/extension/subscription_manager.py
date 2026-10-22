"""
국내주식 WebSocket 구독 관리자

실시간 데이터 구독의 중복을 방지하고 구독 상태를 관리합니다.
"""

from typing import Set, Callable, Any, Optional
import asyncio


class SubscriptionManager:
    """
    WebSocket 구독 중복 방지 및 관리

    종목별 구독 상태를 추적하여 중복 구독을 방지하고,
    보유종목 변경 시 구독 목록을 동기화합니다.
    """

    def __init__(self):
        self._subscribed_symbols: Set[str] = set()
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        symbol: str,
        subscribe_fn: Callable[[str], Any]
    ) -> bool:
        """
        종목 구독 (중복 방지)

        Returns:
            True if newly subscribed, False if already subscribed
        """
        async with self._lock:
            if symbol in self._subscribed_symbols:
                return False

            if asyncio.iscoroutinefunction(subscribe_fn):
                await subscribe_fn(symbol)
            else:
                subscribe_fn(symbol)

            self._subscribed_symbols.add(symbol)
            return True

    async def unsubscribe(
        self,
        symbol: str,
        unsubscribe_fn: Callable[[str], Any]
    ) -> bool:
        """
        종목 구독 해제

        Returns:
            True if unsubscribed, False if not subscribed
        """
        async with self._lock:
            if symbol not in self._subscribed_symbols:
                return False

            if asyncio.iscoroutinefunction(unsubscribe_fn):
                await unsubscribe_fn(symbol)
            else:
                unsubscribe_fn(symbol)

            self._subscribed_symbols.discard(symbol)
            return True

    async def sync_subscriptions(
        self,
        target_symbols: Set[str],
        subscribe_fn: Callable[[str], Any],
        unsubscribe_fn: Callable[[str], Any]
    ):
        """
        보유 종목 변경 시 구독 목록 동기화
        """
        async with self._lock:
            to_subscribe = target_symbols - self._subscribed_symbols
            to_unsubscribe = self._subscribed_symbols - target_symbols

            for symbol in to_unsubscribe:
                try:
                    if asyncio.iscoroutinefunction(unsubscribe_fn):
                        await unsubscribe_fn(symbol)
                    else:
                        unsubscribe_fn(symbol)
                except Exception:
                    pass

            for symbol in to_subscribe:
                try:
                    if asyncio.iscoroutinefunction(subscribe_fn):
                        await subscribe_fn(symbol)
                    else:
                        subscribe_fn(symbol)
                except Exception:
                    pass

            self._subscribed_symbols = target_symbols.copy()

    def is_subscribed(self, symbol: str) -> bool:
        """종목이 구독 중인지 확인"""
        return symbol in self._subscribed_symbols

    @property
    def subscribed_symbols(self) -> Set[str]:
        """현재 구독 중인 종목 목록"""
        return self._subscribed_symbols.copy()

    @property
    def subscription_count(self) -> int:
        """현재 구독 중인 종목 수"""
        return len(self._subscribed_symbols)

    async def clear_all(self, unsubscribe_fn: Optional[Callable[[str], Any]] = None):
        """모든 구독 해제"""
        async with self._lock:
            if unsubscribe_fn:
                for symbol in self._subscribed_symbols:
                    try:
                        if asyncio.iscoroutinefunction(unsubscribe_fn):
                            await unsubscribe_fn(symbol)
                        else:
                            unsubscribe_fn(symbol)
                    except Exception:
                        pass

            self._subscribed_symbols.clear()

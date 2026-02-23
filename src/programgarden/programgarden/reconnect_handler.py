"""
ProgramGarden - ReconnectHandler

WebSocket reconnection handler with:
- Token expiry check and refresh
- Exponential backoff retry
- Maximum retry limit
- Post-reconnection callbacks
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.token_manager import TokenManager

logger = logging.getLogger("programgarden.reconnect")


class ReconnectHandler:
    """
    WebSocket reconnection handler

    Handles disconnection with:
    1. Token expiry check → refresh if needed
    2. Exponential backoff delays
    3. Maximum retry limit (default 5)
    4. Post-reconnection callbacks (resubscribe, order check 등)

    Usage:
        handler = ReconnectHandler(token_manager)
        handler.add_on_reconnect(resubscribe_symbols)

        async def on_disconnect():
            can_retry = await handler.handle_disconnect()
            if can_retry:
                await tracker.reconnect()
                await handler.on_reconnect_success()
            else:
                context.fail_job("Reconnection failed")
    """

    MAX_ATTEMPTS = 5
    BACKOFF_DELAYS = [1, 2, 4, 8, 16]  # seconds

    def __init__(self, token_manager: Optional["TokenManager"] = None):
        """
        Initialize reconnect handler

        Args:
            token_manager: Finance package TokenManager for token refresh
        """
        self._token_manager = token_manager
        self._attempt_count = 0
        self._on_reconnect_callbacks: List[Callable[[], Awaitable[Any]]] = []
        self._total_disconnection_sec: float = 0.0
    
    @property
    def attempt_count(self) -> int:
        """Current retry attempt count"""
        return self._attempt_count
    
    @property
    def has_exceeded_max_attempts(self) -> bool:
        """Check if max retry attempts exceeded"""
        return self._attempt_count >= self.MAX_ATTEMPTS
    
    def add_on_reconnect(self, callback: Callable[[], Awaitable[Any]]) -> None:
        """재연결 성공 시 실행할 콜백 등록 (재구독 등)."""
        self._on_reconnect_callbacks.append(callback)

    async def handle_disconnect(self) -> bool:
        """
        Handle WebSocket disconnection

        Returns:
            True if retry should be attempted, False if should give up
        """
        self._attempt_count += 1

        logger.info(
            f"Reconnect attempt {self._attempt_count}/{self.MAX_ATTEMPTS}"
        )

        if self._attempt_count > self.MAX_ATTEMPTS:
            logger.error(
                f"Max reconnect attempts ({self.MAX_ATTEMPTS}) exceeded. "
                f"총 연결 끊김 시간: {self._total_disconnection_sec:.1f}s. "
                f"이 기간 동안의 체결/시세 데이터가 누락되었을 수 있습니다."
            )
            return False

        # 1. Check and refresh token if expired
        if self._token_manager:
            token_ok = await self._ensure_token()
            if not token_ok:
                logger.error("Token refresh failed - cannot reconnect")
                return False

        # 2. Wait with exponential backoff
        delay = self.BACKOFF_DELAYS[min(self._attempt_count - 1, len(self.BACKOFF_DELAYS) - 1)]
        self._total_disconnection_sec += delay
        logger.info(f"Waiting {delay}s before reconnect... (총 끊김: {self._total_disconnection_sec:.1f}s)")
        await asyncio.sleep(delay)

        return True

    async def on_reconnect_success(self) -> None:
        """재연결 성공 시 호출. 등록된 콜백 실행 후 카운터 리셋."""
        if self._total_disconnection_sec > 0:
            logger.warning(
                f"WebSocket 재연결 성공 (끊김 {self._total_disconnection_sec:.1f}s). "
                f"이 기간 동안 누락된 데이터가 있을 수 있습니다."
            )
        for cb in self._on_reconnect_callbacks:
            try:
                await cb()
            except Exception as e:
                logger.error(f"Reconnect callback 실행 실패: {e}")
        self.reset()
    
    async def _ensure_token(self) -> bool:
        """
        Check token validity and refresh if expired
        
        Returns:
            True if token is valid (or refreshed successfully), False otherwise
        """
        if not self._token_manager:
            return True
        
        try:
            # Check if token is expired (with 5min skew)
            if self._token_manager.is_expired():
                logger.info("Token expired, attempting refresh...")
                
                # Try async refresh
                if hasattr(self._token_manager, 'ensure_fresh_token_async'):
                    refreshed = await self._token_manager.ensure_fresh_token_async()
                else:
                    # Fallback to sync
                    refreshed = self._token_manager.ensure_fresh_token()
                
                if refreshed:
                    logger.info("Token refresh successful")
                    return True
                else:
                    logger.error("Token refresh failed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Token check/refresh error: {e}")
            return False
    
    def reset(self) -> None:
        """
        Reset retry counter (call after successful reconnection)
        """
        if self._attempt_count > 0:
            logger.info(f"Reconnect successful, resetting counter from {self._attempt_count}")
        self._attempt_count = 0
        self._total_disconnection_sec = 0.0
    
    def get_status(self) -> dict:
        """Get current handler status"""
        return {
            "attempt_count": self._attempt_count,
            "max_attempts": self.MAX_ATTEMPTS,
            "has_exceeded": self.has_exceeded_max_attempts,
            "has_token_manager": self._token_manager is not None,
            "total_disconnection_sec": self._total_disconnection_sec,
            "on_reconnect_callbacks": len(self._on_reconnect_callbacks),
        }

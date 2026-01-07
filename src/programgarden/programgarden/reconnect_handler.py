"""
ProgramGarden - ReconnectHandler

WebSocket reconnection handler with:
- Token expiry check and refresh
- Exponential backoff retry
- Maximum retry limit
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

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
    
    Usage:
        handler = ReconnectHandler(token_manager)
        
        async def on_disconnect():
            can_retry = await handler.handle_disconnect()
            if can_retry:
                await tracker.reconnect()
                handler.reset()  # Reset on success
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
    
    @property
    def attempt_count(self) -> int:
        """Current retry attempt count"""
        return self._attempt_count
    
    @property
    def has_exceeded_max_attempts(self) -> bool:
        """Check if max retry attempts exceeded"""
        return self._attempt_count >= self.MAX_ATTEMPTS
    
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
                f"Max reconnect attempts ({self.MAX_ATTEMPTS}) exceeded"
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
        logger.info(f"Waiting {delay}s before reconnect...")
        await asyncio.sleep(delay)
        
        return True
    
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
    
    def get_status(self) -> dict:
        """Get current handler status"""
        return {
            "attempt_count": self._attempt_count,
            "max_attempts": self.MAX_ATTEMPTS,
            "has_exceeded": self.has_exceeded_max_attempts,
            "has_token_manager": self._token_manager is not None,
        }

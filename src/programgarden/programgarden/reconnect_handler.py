"""
ProgramGarden - ReconnectHandler

WebSocket reconnection handler with:
- Token expiry check and refresh
- Exponential backoff retry
- Maximum retry limit
- Post-reconnection callbacks
- Investor notifications (on_notification) for connection lost/restored/failed (C-8)
- Post-reconnect reconcile hook (re-query open-orders/positions; C-8)
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

from programgarden_core.bases.listener import (
    NotificationCategory,
    NotificationSeverity,
)

if TYPE_CHECKING:
    from programgarden_finance.ls.token_manager import TokenManager

logger = logging.getLogger("programgarden.reconnect")

# notify(category, severity, title, message, data) -> awaitable
NotifyCallback = Callable[
    [NotificationCategory, NotificationSeverity, str, str, Dict[str, Any]],
    Awaitable[Any],
]
# reconcile() -> awaitable summary dict (or None). A truthy "drift" key escalates
# the CONNECTION_RESTORED notification severity to WARNING.
ReconcileCallback = Callable[[], Awaitable[Optional[Dict[str, Any]]]]


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

    def __init__(
        self,
        token_manager: Optional["TokenManager"] = None,
        notify: Optional[NotifyCallback] = None,
        reconcile: Optional[ReconcileCallback] = None,
    ):
        """
        Initialize reconnect handler

        Args:
            token_manager: Finance package TokenManager for token refresh
            notify: Optional investor-notification sink. When provided, the handler
                emits CONNECTION_LOST / CONNECTION_RESTORED / CONNECTION_FAILED
                events (C-8). Failures in the sink never abort reconnection.
            reconcile: Optional async hook run once on reconnect success, after
                resubscribe callbacks. Expected to re-query open-orders/positions
                and return a diff summary dict; a truthy "drift" key escalates the
                CONNECTION_RESTORED notification to WARNING (C-8).
        """
        self._token_manager = token_manager
        self._notify = notify
        self._reconcile = reconcile
        self._attempt_count = 0
        self._on_reconnect_callbacks: List[Callable[[], Awaitable[Any]]] = []
        self._total_disconnection_sec: float = 0.0
        # CONNECTION_LOST is emitted once per disconnection episode, not per retry.
        self._lost_notified: bool = False
    
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

        # Promote the disconnection to an investor notification once per episode
        # (not per retry) so telegram/UI surfaces it instead of log-only (C-8).
        if not self._lost_notified:
            self._lost_notified = True
            await self._safe_notify(
                NotificationCategory.CONNECTION_LOST,
                NotificationSeverity.WARNING,
                "실시간 연결 끊김",
                "실시간 WebSocket 연결이 끊겨 재연결을 시도합니다.",
                {"attempt": self._attempt_count, "max_attempts": self.MAX_ATTEMPTS},
            )

        if self._attempt_count > self.MAX_ATTEMPTS:
            logger.error(
                f"Max reconnect attempts ({self.MAX_ATTEMPTS}) exceeded. "
                f"총 연결 끊김 시간: {self._total_disconnection_sec:.1f}s. "
                f"이 기간 동안의 체결/시세 데이터가 누락되었을 수 있습니다."
            )
            await self._safe_notify(
                NotificationCategory.CONNECTION_FAILED,
                NotificationSeverity.CRITICAL,
                "재연결 실패",
                f"최대 재시도({self.MAX_ATTEMPTS}회)를 소진해 재연결에 실패했습니다. "
                f"끊김 {self._total_disconnection_sec:.1f}s 동안 체결/시세가 "
                f"누락되었을 수 있으니 계좌 상태를 확인하세요.",
                {
                    "total_disconnection_sec": self._total_disconnection_sec,
                    "max_attempts": self.MAX_ATTEMPTS,
                },
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
        """재연결 성공 시 호출. 재구독 콜백 → reconcile → 알림 후 카운터 리셋."""
        gap_sec = self._total_disconnection_sec
        if gap_sec > 0:
            logger.warning(
                f"WebSocket 재연결 성공 (끊김 {gap_sec:.1f}s). "
                f"이 기간 동안 누락된 데이터가 있을 수 있습니다."
            )
        # 1. Resubscribe / restore-stream callbacks first (must precede reconcile so
        #    the fresh open-orders/position re-query runs over a live connection).
        for cb in self._on_reconnect_callbacks:
            try:
                await cb()
            except Exception as e:
                logger.error(f"Reconnect callback 실행 실패: {e}")

        # 2. Reconcile: re-query open-orders/positions and detect gap drift (C-8).
        #    Notify-only — never auto-triggers downstream re-evaluation or orders.
        reconcile_summary: Optional[Dict[str, Any]] = None
        if self._reconcile:
            try:
                reconcile_summary = await self._reconcile()
            except Exception as e:
                logger.error(f"Reconnect reconcile 실행 실패: {e}")
                reconcile_summary = {"error": str(e)}

        # 3. Promote the restoration to an investor notification. Escalate to
        #    WARNING when reconcile found drift (fills/cancels/position change
        #    during the gap) or errored, so it is not lost in INFO noise.
        drift = bool(reconcile_summary and (
            reconcile_summary.get("drift") or reconcile_summary.get("error")
        ))
        severity = NotificationSeverity.WARNING if (drift or gap_sec > 0) else NotificationSeverity.INFO
        message = f"실시간 연결이 복구되었습니다 (끊김 {gap_sec:.1f}s)."
        if drift and reconcile_summary and not reconcile_summary.get("error"):
            message += " 끊김 동안 주문/포지션 변동이 감지되었습니다 — 알림 데이터를 확인하세요."
        elif reconcile_summary and reconcile_summary.get("error"):
            message += " 단, 재조회(reconcile)에 실패해 상태 확인이 필요합니다."
        await self._safe_notify(
            NotificationCategory.CONNECTION_RESTORED,
            severity,
            "실시간 연결 복구",
            message,
            {
                "total_disconnection_sec": gap_sec,
                "reconcile": reconcile_summary,
            },
        )
        self._lost_notified = False
        self.reset()

    async def _safe_notify(
        self,
        category: NotificationCategory,
        severity: NotificationSeverity,
        title: str,
        message: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit a notification if a sink is wired; never let it abort reconnection."""
        if not self._notify:
            return
        try:
            await self._notify(category, severity, title, message, data)
        except Exception as e:
            logger.warning(f"Reconnect notification 전파 실패 ({category.value}): {e}")
    
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
        self._lost_notified = False

    def get_status(self) -> dict:
        """Get current handler status"""
        return {
            "attempt_count": self._attempt_count,
            "max_attempts": self.MAX_ATTEMPTS,
            "has_exceeded": self.has_exceeded_max_attempts,
            "has_token_manager": self._token_manager is not None,
            "total_disconnection_sec": self._total_disconnection_sec,
            "on_reconnect_callbacks": len(self._on_reconnect_callbacks),
            "has_notify": self._notify is not None,
            "has_reconcile": self._reconcile is not None,
        }

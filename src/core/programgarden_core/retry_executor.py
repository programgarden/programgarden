"""
RetryExecutor - 재시도 로직 처리 실행기

외부 API를 호출하는 노드의 실패 처리를 위한 공통 재시도 로직.
BaseMessagingNode를 상속하는 노드에서 자동으로 사용됨.

Usage:
    retry_executor = RetryExecutor(listener=my_listener)

    result = await retry_executor.execute_with_retry(
        node=my_node,
        execute_fn=lambda: my_node.execute(context),
        context=context,
    )
"""

import asyncio
import random
import logging
from typing import Optional, Dict, Any, Callable, Awaitable, TYPE_CHECKING

from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
    RetryableError,
    RetryEvent,
)

if TYPE_CHECKING:
    from programgarden_core.bases.listener import ExecutionListener
    from programgarden_core.nodes.base import BaseMessagingNode

logger = logging.getLogger("programgarden.retry_executor")


class RetryExecutor:
    """
    재시도 로직을 처리하는 실행기.

    Exponential backoff with jitter를 사용하여 재시도 간격을 결정.
    모든 재시도 실패 시 FallbackConfig에 따라 처리.

    Example:
        retry_executor = RetryExecutor()

        async def do_api_call():
            return await http_client.get(url)

        result = await retry_executor.execute_with_retry(
            node=my_node,
            execute_fn=do_api_call,
            context=context,
        )
    """

    def __init__(self):
        """Initialize RetryExecutor."""
        pass

    async def execute_with_retry(
        self,
        node: "BaseMessagingNode",
        execute_fn: Callable[[], Awaitable[Dict[str, Any]]],
        context: Any,
    ) -> Dict[str, Any]:
        """
        재시도 로직을 적용하여 노드 실행.

        Args:
            node: BaseMessagingNode 인스턴스 (resilience 설정 포함)
            execute_fn: 실행할 비동기 함수 (노드의 execute 메서드)
            context: ExecutionContext (job_id 등 포함)

        Returns:
            노드 실행 결과 dict

        Raises:
            Exception: 모든 재시도 실패 후 fallback.mode=ERROR인 경우
        """
        config = node.resilience
        last_error: Optional[Exception] = None

        # max_retries + 1 = 최초 시도 + 재시도 횟수
        max_attempts = config.retry.max_retries + 1 if config.retry.enabled else 1

        for attempt in range(1, max_attempts + 1):
            try:
                return await execute_fn()

            except Exception as e:
                last_error = e
                error_type = node.is_retryable_error(e)

                # 재시도 불가능한 에러이거나, retry 비활성화이거나, 마지막 시도인 경우
                if (
                    error_type is None
                    or not config.retry.enabled
                    or error_type not in config.retry.retry_on
                    or attempt >= max_attempts
                ):
                    logger.warning(
                        f"[{node.id}] 재시도 불가 또는 마지막 시도: {e} "
                        f"(error_type={error_type}, attempt={attempt}/{max_attempts})"
                    )
                    break

                # 대기 시간 계산 (exponential backoff with jitter)
                delay = self._calculate_delay(config.retry, attempt)

                logger.info(
                    f"[{node.id}] {error_type.value} 발생, "
                    f"재시도 {attempt}/{config.retry.max_retries}... {delay:.1f}초 후"
                )

                # 재시도 이벤트 발송 (context.notify_retry 사용)
                event = RetryEvent(
                    job_id=getattr(context, "job_id", "unknown"),
                    node_id=node.id,
                    attempt=attempt,
                    max_retries=config.retry.max_retries,
                    error_type=error_type,
                    error_message=str(e),
                    next_retry_in=delay,
                )
                if hasattr(context, "notify_retry"):
                    try:
                        await context.notify_retry(event)
                    except Exception as listener_error:
                        logger.warning(f"context.notify_retry failed: {listener_error}")

                await asyncio.sleep(delay)

        # 모든 재시도 실패: RETRY_EXHAUSTED notification
        if hasattr(context, "send_notification"):
            try:
                from programgarden_core.bases.listener import (
                    NotificationCategory,
                    NotificationSeverity,
                )
                await context.send_notification(
                    category=NotificationCategory.RETRY_EXHAUSTED,
                    severity=NotificationSeverity.WARNING,
                    title=f"Retry exhausted: {node.id}",
                    message=f"{node.__class__.__name__} failed after {config.retry.max_retries} retries: {last_error}",
                    node_id=node.id,
                    node_type=node.__class__.__name__,
                    data={
                        "node_id": node.id,
                        "node_type": node.__class__.__name__,
                        "max_retries": config.retry.max_retries,
                        "last_error": str(last_error),
                    },
                )
            except Exception as notify_err:
                logger.warning(f"RETRY_EXHAUSTED notification failed: {notify_err}")

        # Fallback 처리
        return self._handle_fallback(node, last_error, config.fallback)

    def _calculate_delay(self, config: RetryConfig, attempt: int) -> float:
        """
        대기 시간 계산 (exponential backoff with jitter).

        Args:
            config: RetryConfig
            attempt: 현재 시도 횟수 (1부터 시작)

        Returns:
            대기 시간 (초)
        """
        if config.exponential_backoff:
            # 2^(attempt-1) * base_delay
            # attempt=1 → 1 * base_delay
            # attempt=2 → 2 * base_delay
            # attempt=3 → 4 * base_delay
            delay = config.base_delay * (2 ** (attempt - 1))
        else:
            delay = config.base_delay

        # jitter 추가 (±25%)
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        delay = delay + jitter

        # max_delay 제한
        return min(delay, config.max_delay)

    def _handle_fallback(
        self,
        node: "BaseMessagingNode",
        error: Optional[Exception],
        config: FallbackConfig,
    ) -> Dict[str, Any]:
        """
        Fallback 처리.

        Args:
            node: BaseMessagingNode 인스턴스
            error: 발생한 예외
            config: FallbackConfig

        Returns:
            Fallback 결과 dict (mode=SKIP 또는 DEFAULT_VALUE인 경우)

        Raises:
            Exception: mode=ERROR인 경우 원래 예외 다시 발생
        """
        if error is None:
            error = Exception("Unknown error")

        if config.mode == FallbackMode.ERROR:
            logger.error(f"[{node.id}] 모든 재시도 실패, 워크플로우 중단: {error}")
            raise error

        if config.mode == FallbackMode.SKIP:
            logger.warning(f"[{node.id}] 모든 재시도 실패, 노드 건너뛰기: {error}")
            return {
                "_skipped": True,
                "_error": str(error),
                "_error_type": type(error).__name__,
            }

        if config.mode == FallbackMode.DEFAULT_VALUE:
            if config.default_value is not None:
                logger.warning(
                    f"[{node.id}] 모든 재시도 실패, 기본값 반환: {error}"
                )
                return {
                    **config.default_value,
                    "_fallback": True,
                    "_error": str(error),
                }
            else:
                logger.error(
                    f"[{node.id}] fallback.mode=default_value이지만 default_value가 없습니다"
                )
                raise ValueError(
                    f"fallback.mode=default_value이지만 default_value가 없습니다: {node.id}"
                )

        # 알 수 없는 mode
        raise error


__all__ = ["RetryExecutor"]

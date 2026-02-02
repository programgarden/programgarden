"""
RetryExecutor 단위 테스트

재시도 로직, Exponential backoff, Fallback 처리 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from programgarden_core.retry_executor import RetryExecutor
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
    RetryableError,
    RetryEvent,
)


class MockNode:
    """테스트용 노드 Mock"""

    def __init__(
        self,
        node_id: str = "test_node",
        resilience: ResilienceConfig = None,
    ):
        self.id = node_id
        self.resilience = resilience or ResilienceConfig()

    def is_retryable_error(self, error: Exception) -> RetryableError | None:
        """기본 에러 판단 로직"""
        error_str = str(error).lower()

        if "timeout" in error_str:
            return RetryableError.TIMEOUT
        if "429" in error_str or "rate limit" in error_str:
            return RetryableError.RATE_LIMIT
        if "connection" in error_str:
            return RetryableError.NETWORK_ERROR
        if "500" in error_str or "503" in error_str:
            return RetryableError.SERVER_ERROR

        return None


class MockContext:
    """테스트용 컨텍스트 Mock"""

    def __init__(self, job_id: str = "test_job"):
        self.job_id = job_id
        self.retry_events: list[RetryEvent] = []

    async def notify_retry(self, event: RetryEvent) -> None:
        self.retry_events.append(event)


class TestRetryExecutorBasic:
    """기본 동작 테스트"""

    @pytest.mark.asyncio
    async def test_success_without_retry(self):
        """성공 시 재시도 없이 바로 반환"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=True, max_retries=3)
            )
        )
        context = MockContext()

        async def success_fn():
            return {"result": "ok"}

        result = await executor.execute_with_retry(
            node=node,
            execute_fn=success_fn,
            context=context,
        )

        assert result == {"result": "ok"}
        assert len(context.retry_events) == 0  # 재시도 이벤트 없음

    @pytest.mark.asyncio
    async def test_retry_disabled(self):
        """재시도 비활성화 시 바로 에러 발생"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=False)
            )
        )
        context = MockContext()

        async def fail_fn():
            raise Exception("timeout error")

        with pytest.raises(Exception, match="timeout error"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=fail_fn,
                context=context,
            )

        assert len(context.retry_events) == 0  # 재시도 이벤트 없음


class TestRetryLogic:
    """재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """타임아웃 시 재시도"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(
                    enabled=True,
                    max_retries=2,
                    base_delay=0.2,  # 테스트용 최소값
                )
            )
        )
        context = MockContext()

        call_count = 0

        async def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("timeout error")
            return {"result": "ok"}

        result = await executor.execute_with_retry(
            node=node,
            execute_fn=flaky_fn,
            context=context,
        )

        assert result == {"result": "ok"}
        assert call_count == 2  # 1회 실패 + 1회 성공
        assert len(context.retry_events) == 1  # 1회 재시도 이벤트
        assert context.retry_events[0].error_type == RetryableError.TIMEOUT

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """최대 재시도 횟수 초과 시 에러 발생"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(
                    enabled=True,
                    max_retries=2,
                    base_delay=0.2,
                ),
                fallback=FallbackConfig(mode=FallbackMode.ERROR),
            )
        )
        context = MockContext()

        async def always_fail():
            raise Exception("timeout error")

        with pytest.raises(Exception, match="timeout error"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=always_fail,
                context=context,
            )

        # max_retries=2 → 최초 시도 + 2회 재시도 = 총 3회 시도
        # 재시도 이벤트는 2회 (1번째, 2번째 실패 후)
        assert len(context.retry_events) == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """재시도 불가능한 에러는 바로 실패"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=True, max_retries=3)
            )
        )
        context = MockContext()

        async def permission_error():
            raise Exception("permission denied")

        with pytest.raises(Exception, match="permission denied"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=permission_error,
                context=context,
            )

        assert len(context.retry_events) == 0  # 재시도 없음

    @pytest.mark.asyncio
    async def test_retry_on_filter(self):
        """retry_on 필터링 테스트"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(
                    enabled=True,
                    max_retries=3,
                    retry_on=[RetryableError.RATE_LIMIT],  # RATE_LIMIT만
                )
            )
        )
        context = MockContext()

        async def timeout_error():
            raise Exception("timeout error")

        # TIMEOUT은 retry_on에 없으므로 재시도 없이 바로 실패
        with pytest.raises(Exception, match="timeout error"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=timeout_error,
                context=context,
            )

        assert len(context.retry_events) == 0


class TestFallbackModes:
    """Fallback 모드 테스트"""

    @pytest.mark.asyncio
    async def test_fallback_error(self):
        """ERROR 모드: 예외 다시 발생"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=False),
                fallback=FallbackConfig(mode=FallbackMode.ERROR),
            )
        )
        context = MockContext()

        async def fail_fn():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=fail_fn,
                context=context,
            )

    @pytest.mark.asyncio
    async def test_fallback_skip(self):
        """SKIP 모드: _skipped=True 반환"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=False),
                fallback=FallbackConfig(mode=FallbackMode.SKIP),
            )
        )
        context = MockContext()

        async def fail_fn():
            raise ValueError("test error")

        result = await executor.execute_with_retry(
            node=node,
            execute_fn=fail_fn,
            context=context,
        )

        assert result["_skipped"] is True
        assert "test error" in result["_error"]

    @pytest.mark.asyncio
    async def test_fallback_default_value(self):
        """DEFAULT_VALUE 모드: 기본값 반환"""
        executor = RetryExecutor()
        default_value = {"action": "hold", "reason": "API 실패"}
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=False),
                fallback=FallbackConfig(
                    mode=FallbackMode.DEFAULT_VALUE,
                    default_value=default_value,
                ),
            )
        )
        context = MockContext()

        async def fail_fn():
            raise ValueError("test error")

        result = await executor.execute_with_retry(
            node=node,
            execute_fn=fail_fn,
            context=context,
        )

        assert result["action"] == "hold"
        assert result["reason"] == "API 실패"
        assert result["_fallback"] is True
        assert "test error" in result["_error"]

    @pytest.mark.asyncio
    async def test_fallback_default_value_missing(self):
        """DEFAULT_VALUE 모드: default_value 없으면 에러"""
        executor = RetryExecutor()
        node = MockNode(
            resilience=ResilienceConfig(
                retry=RetryConfig(enabled=False),
                fallback=FallbackConfig(
                    mode=FallbackMode.DEFAULT_VALUE,
                    default_value=None,  # 없음
                ),
            )
        )
        context = MockContext()

        async def fail_fn():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="default_value가 없습니다"):
            await executor.execute_with_retry(
                node=node,
                execute_fn=fail_fn,
                context=context,
            )


class TestDelayCalculation:
    """지연 시간 계산 테스트"""

    def test_exponential_backoff(self):
        """Exponential backoff 테스트"""
        executor = RetryExecutor()
        config = RetryConfig(
            enabled=True,
            base_delay=1.0,
            exponential_backoff=True,
            max_delay=30.0,
        )

        # jitter 없이 정확한 값 확인 불가, 범위로 확인
        delay1 = executor._calculate_delay(config, 1)  # ~1.0
        delay2 = executor._calculate_delay(config, 2)  # ~2.0
        delay3 = executor._calculate_delay(config, 3)  # ~4.0

        # base * 2^(attempt-1) ± 25% jitter
        assert 0.75 <= delay1 <= 1.25  # 1.0 ± 25%
        assert 1.5 <= delay2 <= 2.5    # 2.0 ± 25%
        assert 3.0 <= delay3 <= 5.0    # 4.0 ± 25%

    def test_linear_backoff(self):
        """Linear backoff (exponential=False) 테스트"""
        executor = RetryExecutor()
        config = RetryConfig(
            enabled=True,
            base_delay=2.0,
            exponential_backoff=False,
            max_delay=30.0,
        )

        delay1 = executor._calculate_delay(config, 1)
        delay2 = executor._calculate_delay(config, 2)
        delay3 = executor._calculate_delay(config, 3)

        # 모두 base_delay ± 25% jitter
        assert 1.5 <= delay1 <= 2.5
        assert 1.5 <= delay2 <= 2.5
        assert 1.5 <= delay3 <= 2.5

    def test_max_delay_cap(self):
        """max_delay 제한 테스트"""
        executor = RetryExecutor()
        config = RetryConfig(
            enabled=True,
            base_delay=1.0,
            exponential_backoff=True,
            max_delay=5.0,  # 낮은 상한
        )

        # attempt=10 → 2^9 = 512초 이지만 max_delay=5초로 제한
        delay = executor._calculate_delay(config, 10)
        assert delay <= 5.0 * 1.25  # max_delay + 25% jitter


class TestRetryEvent:
    """RetryEvent 생성 테스트"""

    @pytest.mark.asyncio
    async def test_retry_event_fields(self):
        """RetryEvent 필드 검증"""
        executor = RetryExecutor()
        node = MockNode(
            node_id="my_node",
            resilience=ResilienceConfig(
                retry=RetryConfig(
                    enabled=True,
                    max_retries=3,
                    base_delay=0.2,
                )
            )
        )
        context = MockContext(job_id="job_123")

        call_count = 0

        async def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 rate limit exceeded")
            return {"ok": True}

        await executor.execute_with_retry(
            node=node,
            execute_fn=flaky_fn,
            context=context,
        )

        assert len(context.retry_events) == 1
        event = context.retry_events[0]

        assert event.job_id == "job_123"
        assert event.node_id == "my_node"
        assert event.attempt == 1
        assert event.max_retries == 3
        assert event.error_type == RetryableError.RATE_LIMIT
        assert "rate limit" in event.error_message
        assert event.next_retry_in > 0
        assert isinstance(event.timestamp, datetime)

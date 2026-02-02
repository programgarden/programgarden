"""
Resilience 모델 - Retry/Fallback 공통 시스템

외부 API를 호출하는 노드들의 실패 처리를 위한 공통 모델.
BaseMessagingNode를 상속하는 모든 노드에서 사용.

Usage:
    class MyAPINode(BaseMessagingNode):
        resilience: ResilienceConfig = Field(
            default_factory=lambda: ResilienceConfig(
                retry=RetryConfig(enabled=True, max_retries=3),
                fallback=FallbackConfig(mode=FallbackMode.SKIP),
            )
        )
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class RetryableError(str, Enum):
    """재시도 가능한 에러 유형"""
    TIMEOUT = "timeout"              # 요청 타임아웃
    RATE_LIMIT = "rate_limit"        # Rate limit 초과 (429)
    NETWORK_ERROR = "network_error"  # 네트워크 연결 실패
    SERVER_ERROR = "server_error"    # 서버 오류 (5xx)
    PARSE_ERROR = "parse_error"      # 응답 파싱 실패 (AI 노드용)


class FallbackMode(str, Enum):
    """실패 시 동작 모드"""
    ERROR = "error"                  # 워크플로우 중단 (기본값, 안전)
    SKIP = "skip"                    # 이 노드 건너뛰고 다음으로
    DEFAULT_VALUE = "default_value"  # 기본값 반환


class RetryConfig(BaseModel):
    """
    재시도 설정

    Attributes:
        enabled: 재시도 활성화 여부
        max_retries: 최대 재시도 횟수 (0~10)
        base_delay: 기본 대기 시간 (초)
        exponential_backoff: 지수 백오프 적용 여부
        max_delay: 최대 대기 시간 (초)
        retry_on: 재시도할 에러 유형 목록
    """
    enabled: bool = False
    max_retries: int = Field(default=3, ge=0, le=10)
    base_delay: float = Field(default=1.0, ge=0.1, le=30.0)
    exponential_backoff: bool = True
    max_delay: float = Field(default=30.0, ge=1.0, le=120.0)
    retry_on: List[RetryableError] = Field(
        default_factory=lambda: [
            RetryableError.TIMEOUT,
            RetryableError.RATE_LIMIT,
            RetryableError.NETWORK_ERROR,
            RetryableError.SERVER_ERROR,
        ]
    )


class FallbackConfig(BaseModel):
    """
    실패 처리 설정

    Attributes:
        mode: 실패 시 동작 모드
        default_value: mode=DEFAULT_VALUE일 때 반환할 값
    """
    mode: FallbackMode = FallbackMode.ERROR
    default_value: Optional[Dict[str, Any]] = None


class ResilienceConfig(BaseModel):
    """
    통합 복원력 설정 (Retry + Fallback)

    Attributes:
        retry: 재시도 설정
        fallback: 실패 처리 설정

    Example:
        # 기본 설정 (재시도 비활성화, 실패 시 중단)
        ResilienceConfig()

        # 재시도 3회, 실패 시 건너뛰기
        ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.SKIP),
        )

        # 재시도 5회, 실패 시 기본값 반환
        ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=5),
            fallback=FallbackConfig(
                mode=FallbackMode.DEFAULT_VALUE,
                default_value={"action": "hold", "reason": "API 실패"},
            ),
        )
    """
    retry: RetryConfig = Field(default_factory=RetryConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)


@dataclass
class RetryEvent:
    """
    재시도 이벤트 (Listener 콜백용)

    UI에서 "재시도 중 (2/3)..." 표시용.

    Attributes:
        job_id: Job 식별자
        node_id: 노드 ID
        attempt: 현재 시도 (1부터 시작)
        max_retries: 최대 재시도 횟수
        error_type: 에러 유형
        error_message: 에러 메시지
        next_retry_in: 다음 재시도까지 대기 시간 (초)
        timestamp: 이벤트 발생 시각
    """
    job_id: str
    node_id: str
    attempt: int
    max_retries: int
    error_type: RetryableError
    error_message: str
    next_retry_in: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


__all__ = [
    "RetryableError",
    "FallbackMode",
    "RetryConfig",
    "FallbackConfig",
    "ResilienceConfig",
    "RetryEvent",
]

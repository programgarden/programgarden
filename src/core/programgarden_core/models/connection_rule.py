"""
ProgramGarden Core - 노드 연결 규칙 모델

실시간 노드에서 위험 노드(주문, AI Agent)로의 직접 연결을
구조적으로 방지하기 위한 선언적 규칙 모델.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from enum import Enum


# 실시간(WebSocket) 소스 노드 타입 목록 (6개)
# 이 노드들은 초당 수십~수백 회 트리거되므로 위험 노드(주문/AI/HTTP)에 직결하면 위험
REALTIME_SOURCE_NODE_TYPES: List[str] = [
    "OverseasStockRealMarketDataNode",
    "OverseasFuturesRealMarketDataNode",
    "OverseasStockRealAccountNode",
    "OverseasFuturesRealAccountNode",
    "OverseasStockRealOrderEventNode",
    "OverseasFuturesRealOrderEventNode",
]


class ConnectionSeverity(str, Enum):
    """연결 규칙 위반 시 심각도"""
    ERROR = "error"      # 연결 차단 (저장 불가)
    WARNING = "warning"  # 경고 표시 (저장 가능, 실행 시 재확인)


class ConnectionRule(BaseModel):
    """
    노드 연결 규칙 (선언적)

    이 노드에 특정 소스 노드가 직접 연결될 때의 규칙을 정의.
    프론트엔드에서 엣지 드래그 시 연결 가능 여부를 판단하는 데 사용.

    Examples:
        # 실시간 노드에서 직접 연결 차단, ThrottleNode 경유 필요
        ConnectionRule(
            deny_direct_from=["OverseasStockRealMarketDataNode", ...],
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.ERROR,
            reason="i18n:connection_rules.realtime_to_order.reason",
            suggestion="i18n:connection_rules.realtime_to_order.suggestion",
        )
    """
    # 직접 연결을 차단할 소스 노드 타입 목록
    deny_direct_from: List[str] = Field(
        default_factory=list,
        description="이 노드로 직접 연결을 차단할 소스 노드 타입",
    )

    # 차단된 연결에 대해 경유해야 하는 중간 노드 타입
    required_intermediate: Optional[str] = Field(
        default=None,
        description="차단된 연결에 대해 반드시 경유해야 하는 노드 타입 (예: ThrottleNode)",
    )

    # 심각도 (error: 저장 차단, warning: 경고만)
    severity: ConnectionSeverity = Field(
        default=ConnectionSeverity.ERROR,
        description="위반 시 심각도",
    )

    # 사용자에게 보여줄 이유와 제안 (i18n 키 지원)
    reason: str = Field(
        default="",
        description="차단/경고 이유 (i18n 키 또는 직접 텍스트)",
    )
    suggestion: str = Field(
        default="",
        description="해결 방법 제안 (i18n 키 또는 직접 텍스트)",
    )


class RateLimitConfig(BaseModel):
    """
    노드 레벨 rate limit 설정 (런타임 최후 방어선)

    AIAgentNode의 cooldown_sec + executing 플래그 패턴을 일반화.
    이 설정이 있는 노드는 Executor에서 자동으로 rate limit을 적용.

    Examples:
        # 주문 노드: 같은 노드 인스턴스에서 최소 5초 간격
        RateLimitConfig(
            min_interval_sec=5,
            max_concurrent=1,
            on_throttle="skip",   # 스킵 (주문 중복 방지)
        )

        # AI Agent 노드: 60초 간격, 동시 실행 1개
        RateLimitConfig(
            min_interval_sec=60,
            max_concurrent=1,
            on_throttle="skip",
        )
    """
    # 최소 실행 간격 (초)
    min_interval_sec: float = Field(
        default=0,
        ge=0,
        description="최소 실행 간격 (초). 0이면 제한 없음",
    )

    # 동시 실행 제한
    max_concurrent: int = Field(
        default=0,
        ge=0,
        description="최대 동시 실행 수. 0이면 제한 없음",
    )

    # 제한 도달 시 동작
    on_throttle: Literal["skip", "queue", "error"] = Field(
        default="skip",
        description="rate limit 도달 시 동작: skip(무시), queue(대기), error(실패)",
    )

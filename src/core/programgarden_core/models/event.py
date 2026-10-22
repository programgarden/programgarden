"""
ProgramGarden Core - Event 모델

이벤트 히스토리 (Event Layer)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class EventType(str, Enum):
    """이벤트 유형"""

    # 워크플로우 이벤트
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # 스케줄 이벤트
    SCHEDULE_TRIGGERED = "schedule_triggered"

    # 조건 이벤트
    CONDITION_EVALUATED = "condition_evaluated"
    CONDITION_PASSED = "condition_passed"
    CONDITION_FAILED = "condition_failed"

    # 주문 이벤트
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIAL_FILLED = "order_partial_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_MODIFIED = "order_modified"

    # 리스크 이벤트
    RISK_TRIGGERED = "risk_triggered"
    RISK_BLOCKED = "risk_blocked"

    # 에러 이벤트
    ERROR_OCCURRED = "error_occurred"
    ERROR_RECOVERED = "error_recovered"

    # 알림 이벤트
    ALERT_SENT = "alert_sent"

    # 데이터 이벤트
    DATA_RECEIVED = "data_received"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"


class Event(BaseModel):
    """
    이벤트 히스토리 (Event Layer)

    모든 조건 평가 결과, 주문 체결, 에러 등 이벤트 저장.
    AI가 "어제 왜 매수 안 했어?" 분석 가능.
    백테스팅, 성과 분석 기반 데이터.
    """

    event_id: str = Field(..., description="이벤트 고유 ID")
    job_id: str = Field(..., description="관련 Job ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="이벤트 발생 시간",
    )

    # 이벤트 정보
    type: EventType = Field(..., description="이벤트 유형")
    node_id: Optional[str] = Field(
        default=None,
        description="관련 노드 ID",
    )

    # 이벤트 데이터
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="이벤트 상세 데이터",
    )

    # 메타데이터
    level: str = Field(
        default="info",
        description="로그 레벨 (debug, info, warning, error)",
    )
    message: Optional[str] = Field(
        default=None,
        description="이벤트 메시지",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )


class EventFilter(BaseModel):
    """이벤트 조회 필터"""

    job_id: Optional[str] = None
    event_types: Optional[List[EventType]] = None
    node_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# 타입 힌트용 import
from typing import List

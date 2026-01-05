"""
ProgramGarden Core - Job 모델

워크플로우 실행 인스턴스 (Job Layer)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Job 상태"""

    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 실행 중
    PAUSED = "paused"  # 일시정지
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패
    CANCELLED = "cancelled"  # 취소


class PositionInfo(BaseModel):
    """보유 포지션 정보"""

    symbol: str = Field(..., description="종목 코드")
    quantity: int = Field(..., description="보유 수량")
    entry_price: float = Field(..., description="평균 매입가")
    entry_time: Optional[datetime] = Field(default=None, description="진입 시간")
    current_price: Optional[float] = Field(default=None, description="현재가")
    unrealized_pnl: Optional[float] = Field(default=None, description="미실현 손익")
    pnl_rate: Optional[float] = Field(default=None, description="수익률 (%)")


class PendingOrderInfo(BaseModel):
    """미체결 주문 정보"""

    order_id: str = Field(..., description="주문 ID")
    symbol: str = Field(..., description="종목 코드")
    side: str = Field(..., description="매수/매도 (buy/sell)")
    order_type: str = Field(..., description="주문 유형 (market/limit)")
    quantity: int = Field(..., description="주문 수량")
    price: Optional[float] = Field(default=None, description="주문 가격 (지정가)")
    status: str = Field(default="pending", description="주문 상태")
    created_at: Optional[datetime] = Field(default=None, description="주문 시간")


class ConditionState(BaseModel):
    """조건 노드 상태"""

    last_value: Optional[Any] = Field(default=None, description="마지막 평가 값")
    triggered_at: Optional[datetime] = Field(default=None, description="마지막 트리거 시간")
    passed_count: int = Field(default=0, description="통과 횟수")
    failed_count: int = Field(default=0, description="실패 횟수")


class JobState(BaseModel):
    """
    Job 상태 스냅샷

    Graceful Restart를 위한 상태 보존.
    pause_job() 시 자동 저장, resume_job() 시 복원.
    """

    job_id: str = Field(..., description="Job ID")
    paused_at: Optional[datetime] = Field(default=None, description="일시정지 시간")

    # 포지션 상태
    positions: Dict[str, PositionInfo] = Field(
        default_factory=dict,
        description="보유 포지션 (종목코드별)",
    )

    # 잔고 상태
    balances: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="통화별 잔고 (예: {'USD': {'available': 45000, 'total': 50000}})",
    )

    # 미체결 주문
    pending_orders: List[PendingOrderInfo] = Field(
        default_factory=list,
        description="미체결 주문 목록",
    )

    # 조건 노드 상태
    condition_states: Dict[str, ConditionState] = Field(
        default_factory=dict,
        description="조건 노드별 상태 (node_id별)",
    )

    # 전략 컨텍스트 (사용자 정의)
    strategy_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="전략별 커스텀 상태 (예: phase, trade_count_today)",
    )

    can_restore: bool = Field(
        default=True,
        description="상태 복원 가능 여부",
    )


class WorkflowJob(BaseModel):
    """
    워크플로우 실행 인스턴스 (Job Layer)

    같은 Definition으로 여러 Job을 동시 실행 가능.
    Stateful: 포지션/잔고 상태 유지.
    Graceful Restart 지원.
    """

    job_id: str = Field(..., description="Job 고유 ID")
    workflow_id: str = Field(..., description="참조 Workflow ID")
    workflow_version: str = Field(..., description="참조 Workflow 버전")

    # 상태
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="현재 상태",
    )

    # 실행 컨텍스트 (Definition inputs에 바인딩)
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="실행 컨텍스트 (credential_id, symbols 등)",
    )

    # 타임스탬프
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="생성 시간",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="시작 시간",
    )
    paused_at: Optional[datetime] = Field(
        default=None,
        description="일시정지 시간",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="완료 시간",
    )

    # 실행 통계
    state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "last_trigger": None,
            "conditions_evaluated": 0,
            "orders_placed": 0,
            "orders_filled": 0,
            "orders_cancelled": 0,
            "errors_count": 0,
        },
        description="실행 상태 통계",
    )

    # 에러 정보
    last_error: Optional[str] = Field(
        default=None,
        description="마지막 에러 메시지",
    )

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

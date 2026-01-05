"""
ProgramGarden Core - Event 노드

이벤트/알림 노드:
- EventHandlerNode: 주문 이벤트 처리
- ErrorHandlerNode: 에러 처리 및 복구
- AlertNode: 알림 발송
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class EventHandlerNode(BaseNode):
    """
    주문 이벤트 처리 노드

    체결, 거부, 취소 등 이벤트 발생 시 후속 액션 수행
    """

    type: Literal["EventHandlerNode"] = "EventHandlerNode"
    category: NodeCategory = NodeCategory.EVENT

    # EventHandlerNode 전용 설정
    event: Literal["filled", "rejected", "cancelled", "partial_filled", "all"] = Field(
        default="all",
        description="처리할 이벤트 유형",
    )
    actions: List[str] = Field(
        default=["log"],
        description="수행할 액션 목록 (log, notify, trigger 등)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="order_event",
            description="주문 이벤트 (RealOrderEventNode에서)",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="event",
            type="event_data",
            description="처리된 이벤트 데이터",
        ),
        OutputPort(
            name="trigger",
            type="signal",
            description="후속 액션 트리거",
        ),
    ]


class ErrorHandlerNode(BaseNode):
    """
    에러 처리 및 복구 노드

    실행 중 발생하는 에러 처리 및 복구 로직
    """

    type: Literal["ErrorHandlerNode"] = "ErrorHandlerNode"
    category: NodeCategory = NodeCategory.EVENT

    # ErrorHandlerNode 전용 설정
    error_types: List[str] = Field(
        default=["all"],
        description="처리할 에러 유형 (connection, order, validation, all 등)",
    )
    retry_count: int = Field(
        default=3,
        description="재시도 횟수",
    )
    retry_delay_sec: int = Field(
        default=5,
        description="재시도 간격 (초)",
    )
    fallback_action: Literal["ignore", "alert", "pause_job", "cancel_orders"] = Field(
        default="alert",
        description="재시도 실패 시 대체 액션",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="error",
            type="error_event",
            description="에러 이벤트",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="recovered",
            type="signal",
            description="복구 성공 시 신호",
        ),
        OutputPort(
            name="failed",
            type="signal",
            description="복구 실패 시 신호",
        ),
        OutputPort(
            name="error_data",
            type="error_data",
            description="에러 상세 정보",
        ),
    ]


class AlertNode(BaseNode):
    """
    알림 발송 노드

    Slack, Telegram, Email, Webhook 등으로 알림 발송
    """

    type: Literal["AlertNode"] = "AlertNode"
    category: NodeCategory = NodeCategory.EVENT

    # AlertNode 전용 설정
    channel: Literal["slack", "telegram", "email", "webhook"] = Field(
        default="slack",
        description="알림 채널",
    )
    on: List[str] = Field(
        default=["order_filled", "risk_triggered", "error"],
        description="알림 발송 이벤트 유형",
    )
    template: Optional[str] = Field(
        default=None,
        description="메시지 템플릿 (변수: {symbol}, {side}, {price}, {quantity} 등)",
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL (channel=webhook 시)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="event_data",
            description="알림 트리거 이벤트",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="알림 발송 완료 신호",
        ),
    ]

"""
ProgramGarden Core - Trigger 노드

트리거/필터 노드:
- ScheduleNode: 크론 스케줄 트리거
- TradingHoursFilterNode: 거래시간 필터
- ExchangeStatusNode: 거래소 상태 체크
"""

from typing import Optional, List, Literal
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class ScheduleNode(BaseNode):
    """
    크론 스케줄 트리거 노드

    지정된 크론 표현식에 따라 트리거 신호 발생
    """

    type: Literal["ScheduleNode"] = "ScheduleNode"
    category: NodeCategory = NodeCategory.TRIGGER

    # ScheduleNode 전용 설정
    cron: str = Field(
        default="*/5 * * * *",
        description="크론 표현식 (예: */5 * * * * = 5분마다)",
    )
    timezone: str = Field(
        default="America/New_York", description="타임존 (예: America/New_York, Asia/Seoul)"
    )
    enabled: bool = Field(default=True, description="스케줄 활성화 여부")

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="trigger", type="signal", description="스케줄 트리거 신호")
    ]


class TradingHoursFilterNode(BaseNode):
    """
    거래시간 필터 노드

    지정된 거래시간 내에만 신호 통과
    """

    type: Literal["TradingHoursFilterNode"] = "TradingHoursFilterNode"
    category: NodeCategory = NodeCategory.TRIGGER

    # TradingHoursFilterNode 전용 설정
    start: str = Field(default="09:30", description="시작 시간 (HH:MM)")
    end: str = Field(default="16:00", description="종료 시간 (HH:MM)")
    timezone: str = Field(
        default="America/New_York", description="타임존 (예: America/New_York)"
    )
    days: List[str] = Field(
        default=["mon", "tue", "wed", "thu", "fri"],
        description="활성화 요일 (mon, tue, wed, thu, fri, sat, sun)",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="입력 트리거 신호"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="passed", type="signal", description="거래시간 내 통과 신호"
        ),
        OutputPort(
            name="blocked", type="signal", description="거래시간 외 차단 신호"
        ),
    ]


class ExchangeStatusNode(BaseNode):
    """
    거래소 상태 체크 노드

    거래소 개장/폐장/휴장 상태 확인
    """

    type: Literal["ExchangeStatusNode"] = "ExchangeStatusNode"
    category: NodeCategory = NodeCategory.TRIGGER

    # ExchangeStatusNode 전용 설정
    exchange: str = Field(
        default="NYSE", description="거래소 코드 (NYSE, NASDAQ, CME 등)"
    )
    check_holidays: bool = Field(
        default=True, description="공휴일 체크 여부"
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="입력 트리거 신호"),
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결 (거래소 상태 조회용)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="open", type="signal", description="거래소 개장 시 신호"),
        OutputPort(name="closed", type="signal", description="거래소 폐장 시 신호"),
        OutputPort(name="holiday", type="signal", description="휴장일 시 신호"),
    ]

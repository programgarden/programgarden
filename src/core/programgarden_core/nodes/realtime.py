"""
ProgramGarden Core - Realtime 노드

실시간 스트림 관련 노드:
- RealMarketDataNode: WebSocket 시세 스트림
- RealAccountNode: 실시간 계좌 정보
- RealOrderEventNode: 실시간 주문 이벤트
"""

from typing import Optional, List, Literal
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class RealMarketDataNode(BaseNode):
    """
    실시간 시세 스트림 노드

    WebSocket을 통해 실시간 시세 데이터(price, volume, bid/ask) 수신
    """

    type: Literal["RealMarketDataNode"] = "RealMarketDataNode"
    category: NodeCategory = NodeCategory.REALTIME

    # RealMarketDataNode 전용 설정
    fields: List[str] = Field(
        default=["price", "volume"],
        description="수신할 필드 목록 (price, volume, bid, ask, etc.)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결",
        ),
        InputPort(
            name="symbols", type="symbol_list", description="구독할 종목 리스트"
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="price", type="market_data", description="실시간 가격 데이터"),
        OutputPort(
            name="volume", type="market_data", description="실시간 거래량 데이터"
        ),
        OutputPort(name="bid", type="market_data", description="실시간 매수호가"),
        OutputPort(name="ask", type="market_data", description="실시간 매도호가"),
    ]


class RealAccountNode(BaseNode):
    """
    실시간 계좌 정보 노드

    보유종목, 예수금, 미체결, 실시간 수익률 등 계좌 정보 제공.
    내부적으로 StockAccountTracker를 사용하여 실시간 수익률 계산.

    - 1분마다 REST API로 증권사 데이터와 동기화
    - WebSocket 틱 수신 시 즉시 수익률 재계산
    """

    type: Literal["RealAccountNode"] = "RealAccountNode"
    category: NodeCategory = NodeCategory.REALTIME

    # RealAccountNode 전용 설정
    sync_interval_sec: int = Field(
        default=60, description="REST API 동기화 주기 (초)"
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="held_symbols", type="symbol_list", description="보유종목 코드 리스트"
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="예수금/매수가능금액 (통화별)",
        ),
        OutputPort(
            name="open_orders", type="order_list", description="미체결 주문 목록"
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="보유종목 상세 (실시간 수익률 포함)",
        ),
    ]


class RealOrderEventNode(BaseNode):
    """
    실시간 주문 이벤트 노드

    주문 체결/거부/취소 이벤트 실시간 수신
    """

    type: Literal["RealOrderEventNode"] = "RealOrderEventNode"
    category: NodeCategory = NodeCategory.REALTIME

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="filled", type="order_event", description="체결 이벤트"),
        OutputPort(name="rejected", type="order_event", description="거부 이벤트"),
        OutputPort(name="cancelled", type="order_event", description="취소 이벤트"),
    ]

"""
ProgramGarden Core - Data 노드

데이터 조회 노드 (REST API 1회성):
- MarketDataNode: REST API 시세 조회
- AccountNode: REST API 계좌 조회
"""

from typing import Optional, List, Literal
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class MarketDataNode(BaseNode):
    """
    REST API 1회성 시세 조회 노드

    특정 시점의 시세 데이터를 REST API로 조회
    """

    type: Literal["MarketDataNode"] = "MarketDataNode"
    category: NodeCategory = NodeCategory.DATA

    # MarketDataNode 전용 설정
    fields: List[str] = Field(
        default=["price", "volume", "ohlcv"],
        description="조회할 필드 목록",
    )
    period: Optional[str] = Field(
        default=None, description="OHLCV 조회 시 기간 (예: 1d, 1h, 5m)"
    )
    count: int = Field(default=100, description="OHLCV 조회 시 데이터 개수")

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결",
        ),
        InputPort(
            name="symbols", type="symbol_list", description="조회할 종목 리스트"
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="조회 트리거",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="price", type="market_data", description="현재가 데이터"),
        OutputPort(name="volume", type="market_data", description="거래량 데이터"),
        OutputPort(name="ohlcv", type="ohlcv_data", description="OHLCV 데이터"),
    ]


class AccountNode(BaseNode):
    """
    REST API 1회성 계좌 조회 노드

    특정 시점의 계좌 정보를 REST API로 조회
    """

    type: Literal["AccountNode"] = "AccountNode"
    category: NodeCategory = NodeCategory.DATA

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="BrokerNode 연결",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="조회 트리거",
            required=False,
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
            description="보유종목 상세",
        ),
    ]

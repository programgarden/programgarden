"""
ProgramGarden Core - Order 노드

주문 실행 노드:
- NewOrderNode: 신규 주문 플러그인 실행
- ModifyOrderNode: 정정 주문 플러그인 실행
- CancelOrderNode: 취소 주문 플러그인 실행
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class NewOrderNode(PluginNode):
    """
    신규 주문 플러그인 실행 노드

    MarketOrder, LimitOrder, ATRTrailingStop 등 신규 주문 플러그인 실행
    """

    type: Literal["NewOrderNode"] = "NewOrderNode"
    category: NodeCategory = NodeCategory.ORDER

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="주문 대상 종목 리스트",
        ),
        InputPort(
            name="quantity",
            type="dict",
            description="종목별 주문 수량 (PositionSizingNode에서)",
            required=False,
        ),
        InputPort(
            name="held_symbols",
            type="symbol_list",
            description="현재 보유 종목 (중복 매수 방지용)",
            required=False,
        ),
        InputPort(
            name="balance",
            type="balance_data",
            description="계좌 잔고 정보",
            required=False,
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="현재가 정보 (지정가 주문용)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="order_result",
            type="order_result",
            description="주문 실행 결과",
        ),
        OutputPort(
            name="order_id",
            type="string",
            description="주문 번호",
        ),
        OutputPort(
            name="submitted_orders",
            type="order_list",
            description="제출된 주문 목록",
        ),
    ]


class ModifyOrderNode(PluginNode):
    """
    정정 주문 플러그인 실행 노드

    TrackingPriceModifier, TurtleAdaptiveModify 등 정정 주문 플러그인 실행
    """

    type: Literal["ModifyOrderNode"] = "ModifyOrderNode"
    category: NodeCategory = NodeCategory.ORDER

    _inputs: List[InputPort] = [
        InputPort(
            name="target_orders",
            type="order_list",
            description="정정 대상 미체결 주문 (RealAccountNode.open_orders에서)",
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="현재가 정보 (가격 추적용)",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="modify_result",
            type="order_result",
            description="정정 실행 결과",
        ),
        OutputPort(
            name="modified_orders",
            type="order_list",
            description="정정된 주문 목록",
        ),
    ]


class CancelOrderNode(PluginNode):
    """
    취소 주문 플러그인 실행 노드

    PriceRangeCanceller, TimeStopCanceller 등 취소 주문 플러그인 실행
    """

    type: Literal["CancelOrderNode"] = "CancelOrderNode"
    category: NodeCategory = NodeCategory.ORDER

    _inputs: List[InputPort] = [
        InputPort(
            name="target_orders",
            type="order_list",
            description="취소 대상 미체결 주문 (RealAccountNode.open_orders에서)",
        ),
        InputPort(
            name="price_data",
            type="market_data",
            description="현재가 정보 (가격 범위 체크용)",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="cancel_result",
            type="order_result",
            description="취소 실행 결과",
        ),
        OutputPort(
            name="cancelled_orders",
            type="order_list",
            description="취소된 주문 목록",
        ),
    ]

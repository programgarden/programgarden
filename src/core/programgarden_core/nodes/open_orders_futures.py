"""
ProgramGarden Core - Futures Open Orders Node

해외선물 미체결 주문 조회:
- OverseasFuturesOpenOrdersNode: 해외선물 미체결 주문 조회 (REST API 1회성)
"""

from typing import List, Literal, Dict, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    OPEN_ORDER_FIELDS,
)


class OverseasFuturesOpenOrdersNode(BaseNode):
    """
    해외선물 미체결 주문 조회 노드

    REST API로 현재 미체결 주문 목록을 조회합니다:
    - 주문번호, 종목코드, 매매구분
    - 주문수량, 체결수량, 미체결수량
    - 주문가격, 주문시각

    미체결 주문을 수정하거나 취소할 때 활용합니다.
    """

    type: Literal["OverseasFuturesOpenOrdersNode"] = "OverseasFuturesOpenOrdersNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasFuturesOpenOrdersNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/open_orders_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="open_orders", type="order_list", description="i18n:ports.open_orders", fields=OPEN_ORDER_FIELDS),
        OutputPort(name="count", type="number", description="i18n:ports.count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}

"""
ProgramGarden Core - Korea Stock Account Node

국내주식 계좌 조회:
- KoreaStockAccountNode: 국내주식 계좌 잔고, 보유종목 조회 (REST API 1회성)
"""

from typing import List, Literal, Dict, ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    KOREA_STOCK_BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class KoreaStockAccountNode(BaseNode):
    """
    국내주식 REST API 1회성 계좌 조회 노드

    특정 시점의 국내주식 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산

    미체결 주문 조회는 KoreaStockOpenOrdersNode를 사용하세요.
    실시간 업데이트가 필요하면 KoreaStockRealAccountNode를 사용하세요.
    """

    type: Literal["KoreaStockAccountNode"] = "KoreaStockAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.KoreaStockAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="balance", type="balance_data", description="i18n:ports.balance", fields=KOREA_STOCK_BALANCE_FIELDS),
        OutputPort(name="positions", type="position_data", description="i18n:ports.positions", fields=POSITION_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}

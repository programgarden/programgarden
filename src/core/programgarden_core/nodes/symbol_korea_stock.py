"""
ProgramGarden Core - Korea Stock Symbol Query Node

국내주식 전체종목조회:
- KoreaStockSymbolQueryNode: KOSPI/KOSDAQ 전체 거래 가능 종목 조회 (t9945 API)
"""

from typing import Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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
    SYMBOL_LIST_FIELDS,
)


class KoreaStockSymbolQueryNode(BaseNode):
    """
    국내주식 전체종목조회 노드

    KOSPI/KOSDAQ 전체 거래 가능 종목을 조회합니다.
    t9945 API (마스터상장종목조회) 사용.
    """

    type: Literal["KoreaStockSymbolQueryNode"] = "KoreaStockSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockSymbolQueryNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/symbolquery_korea_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    market: str = Field(
        default="all",
        description="Market type: all, KOSPI, KOSDAQ",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "market": FieldSchema(
                name="market",
                type=FieldType.ENUM,
                description="i18n:fields.KoreaStockSymbolQueryNode.market",
                default="all",
                enum_values=["all", "KOSPI", "KOSDAQ"],
                enum_labels={
                    "all": "i18n:enums.kr_market.all",
                    "KOSPI": "i18n:enums.kr_market.KOSPI",
                    "KOSDAQ": "i18n:enums.kr_market.KOSDAQ",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="all",
                expected_type="str",
            ),
        }

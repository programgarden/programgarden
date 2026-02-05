"""
ProgramGarden Core - Stock Symbol Query Node

해외주식 전체종목조회:
- OverseasStockSymbolQueryNode: 해외주식 전체 거래 가능 종목 조회 (g3190 API)
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


class OverseasStockSymbolQueryNode(BaseNode):
    """
    해외주식 전체종목조회 노드

    해외주식 전체 거래 가능 종목을 조회합니다.
    g3190 API (마스터상장종목조회) 사용.
    """

    type: Literal["OverseasStockSymbolQueryNode"] = "OverseasStockSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockSymbolQueryNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/symbolquery_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    stock_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_stock: NYSE(81), NASDAQ(82), AMEX(83), etc.",
    )
    country: str = Field(
        default="US",
        description="Country code for overseas_stock (US, HK, JP, CN, etc.)",
    )
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
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
            "country": FieldSchema(
                name="country",
                type=FieldType.ENUM,
                description="국가 코드. US: 미국, HK: 홍콩, JP: 일본, CN: 중국",
                default="US",
                enum_values=["US", "HK", "JP", "CN", "VN", "ID"],
                enum_labels={
                    "US": "i18n:enums.country.US",
                    "HK": "i18n:enums.country.HK",
                    "JP": "i18n:enums.country.JP",
                    "CN": "i18n:enums.country.CN",
                    "VN": "i18n:enums.country.VN",
                    "ID": "i18n:enums.country.ID",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="US",
                expected_type="str",
            ),
            "stock_exchange": FieldSchema(
                name="stock_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. NYSE/AMEX: 81, NASDAQ: 82, 전체: 빈값",
                enum_values=["", "81", "82"],
                enum_labels={
                    "": "i18n:enums.stock_exchange_code.all",
                    "81": "i18n:enums.stock_exchange_code.81",
                    "82": "i18n:enums.stock_exchange_code.82",
                },
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="82",
                expected_type="str",
            ),
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=500,
                expected_type="int",
            ),
        }

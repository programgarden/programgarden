"""
ProgramGarden Core - Korea Stock Market Data Node

국내주식 시세 조회:
- KoreaStockMarketDataNode: 국내주식 REST API 시세 조회 (KRX)

Item-based execution:
- Input: 단일 symbol (SplitNode에서 분리된 아이템)
- Output: 단일 value (해당 종목의 시세)
"""

from typing import List, Literal, Dict, ClassVar, Optional, TYPE_CHECKING
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
    KOREA_STOCK_PRICE_DATA_FIELDS,
)


class KoreaStockMarketDataNode(BaseNode):
    """
    국내주식 REST API 시세 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 시세를 조회합니다.
    거래소: KRX (KOSPI, KOSDAQ)

    Item-based execution:
    - Input: symbol (단일 종목 {symbol})
    - Output: value (해당 종목의 시세 데이터)
    """

    type: Literal["KoreaStockMarketDataNode"] = "KoreaStockMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/marketdata_korea_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution) - 국내주식은 exchange 불필요
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with symbol code (6-digit)",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="market_data", description="i18n:ports.market_data_value", fields=KOREA_STOCK_PRICE_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockMarketDataNode.symbol",
                description="i18n:fields.KoreaStockMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"symbol": "005930"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{symbol: str}",
                help_text="i18n:fields.KoreaStockMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.KoreaStockMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
        }

"""
ProgramGarden Core - Futures Market Data Node

해외선물 시세 조회:
- OverseasFuturesMarketDataNode: 해외선물 REST API 시세 조회 (CME, EUREX, SGX, HKEX)

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
    PRICE_DATA_FIELDS,
)


class OverseasFuturesMarketDataNode(BaseNode):
    """
    해외선물 REST API 시세 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 시세를 조회합니다.
    거래소: CME, EUREX, SGX, HKEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 시세 데이터)
    """

    type: Literal["OverseasFuturesMarketDataNode"] = "OverseasFuturesMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/marketdata_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution)
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with exchange and symbol code",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="market_data", description="i18n:ports.market_data_value", fields=PRICE_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasFuturesMarketDataNode.symbol",
                description="i18n:fields.OverseasFuturesMarketDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "CME", "symbol": "ESH26"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasFuturesMarketDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbol.symbol", "required": True},
                ],
            ),
        }

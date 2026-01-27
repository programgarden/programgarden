"""
ProgramGarden Core - Futures Market Data Node

해외선물 시세 조회:
- OverseasFuturesMarketDataNode: 해외선물 REST API 시세 조회 (CME, EUREX, SGX, HKEX)
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
)


class OverseasFuturesMarketDataNode(BaseNode):
    """
    해외선물 REST API 시세 조회 노드

    특정 시점의 해외선물 시세를 REST API로 조회합니다.
    거래소: CME, EUREX, SGX, HKEX
    """

    type: Literal["OverseasFuturesMarketDataNode"] = "OverseasFuturesMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/marketdata_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
    )

    _inputs: List[InputPort] = [
        InputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="values", type="market_data_list", description="i18n:ports.market_data_values"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                display_name="i18n:fieldNames.OverseasFuturesMarketDataNode.symbols",
                description="i18n:fields.OverseasFuturesMarketDataNode.symbols",
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "CME", "symbol": "ESH26"}, {"exchange": "EUREX", "symbol": "FDXH26"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                ],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                help_text="i18n:fields.OverseasFuturesMarketDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesMarketDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "ESH26"},
                ],
                ui_options={
                    "exchanges": [
                        {"value": "CME", "label": "CME (시카고상업거래소)"},
                        {"value": "EUREX", "label": "EUREX (유럽선물거래소)"},
                        {"value": "SGX", "label": "SGX (싱가포르거래소)"},
                        {"value": "HKEX", "label": "HKEX (홍콩선물거래소)"},
                    ],
                },
            ),
        }

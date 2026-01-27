"""
ProgramGarden Core - Stock Market Data Node

해외주식 시세 조회:
- OverseasStockMarketDataNode: 해외주식 REST API 시세 조회 (NYSE, NASDAQ, AMEX)
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


class OverseasStockMarketDataNode(BaseNode):
    """
    해외주식 REST API 시세 조회 노드

    특정 시점의 해외주식 시세를 REST API로 조회합니다.
    거래소: NYSE, NASDAQ, AMEX
    """

    type: Literal["OverseasStockMarketDataNode"] = "OverseasStockMarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockMarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/marketdata_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
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
                display_name="i18n:fieldNames.OverseasStockMarketDataNode.symbols",
                description="i18n:fields.OverseasStockMarketDataNode.symbols",
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "TSLA"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                    "ScreenerNode.symbols",
                    "MarketUniverseNode.symbols",
                ],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                help_text="i18n:fields.OverseasStockMarketDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasStockMarketDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockMarketDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "AAPL"},
                ],
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                    ],
                },
            ),
        }

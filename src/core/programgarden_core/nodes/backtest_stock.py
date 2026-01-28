"""
ProgramGarden Core - Stock Historical Data Node

해외주식 과거 데이터 조회:
- OverseasStockHistoricalDataNode: 해외주식 과거 OHLCV 데이터 조회 (NYSE, NASDAQ, AMEX)
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
    HISTORICAL_DATA_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class OverseasStockHistoricalDataNode(BaseNode):
    """
    해외주식 과거 데이터 조회 노드

    해외주식 종목의 과거 OHLCV 데이터를 조회합니다.
    거래소: NYSE, NASDAQ, AMEX
    """

    type: Literal["OverseasStockHistoricalDataNode"] = "OverseasStockHistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockHistoricalDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/historicaldata_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    symbols: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Target symbols with exchange [{exchange, symbol}]",
    )
    start_date: str = Field(
        default="{{ months_ago_yyyymmdd(3) }}",
        description="Start date (YYYY-MM-DD or {{ months_ago_yyyymmdd(N) }})",
    )
    end_date: str = Field(
        default="{{ today_yyyymmdd() }}",
        description="End date (YYYY-MM-DD or {{ today_yyyymmdd() }})",
    )
    interval: str = Field(
        default="1d",
        description="Data interval (1m, 5m, 15m, 1h, 1d)",
    )
    adjust: bool = Field(
        default=False,
        description="Apply adjusted prices",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="values", type="array", description="i18n:ports.values", fields=HISTORICAL_DATA_FIELDS),
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.symbols",
                description="i18n:fields.OverseasStockHistoricalDataNode.symbols",
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NYSE", "symbol": "IBM"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                    "ScreenerNode.symbols",
                    "MarketUniverseNode.symbols",
                ],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
                help_text="i18n:fields.OverseasStockHistoricalDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasStockHistoricalDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockHistoricalDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "AAPL"},
                ],
                ui_options={
                    "exchanges": [
                        {"value": "NASDAQ", "label": "NASDAQ"},
                        {"value": "NYSE", "label": "NYSE"},
                        {"value": "AMEX", "label": "AMEX"},
                    ],
                },
            ),
            "start_date": FieldSchema(
                name="start_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.start_date",
                description="i18n:fields.OverseasStockHistoricalDataNode.start_date",
                default="{{ months_ago_yyyymmdd(3) }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-01-01",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.OverseasStockHistoricalDataNode.start_date.help_text",
            ),
            "end_date": FieldSchema(
                name="end_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.end_date",
                description="i18n:fields.OverseasStockHistoricalDataNode.end_date",
                default="{{ today_yyyymmdd() }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-12-31",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.OverseasStockHistoricalDataNode.end_date.help_text",
            ),
            "interval": FieldSchema(
                name="interval",
                type=FieldType.ENUM,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.interval",
                description="i18n:fields.OverseasStockHistoricalDataNode.interval",
                default="1d",
                required=True,
                enum_values=["1m", "5m", "15m", "1h", "1d", "1w", "1M"],
                enum_labels={
                    "1m": "i18n:enums.interval.1m",
                    "5m": "i18n:enums.interval.5m",
                    "15m": "i18n:enums.interval.15m",
                    "1h": "i18n:enums.interval.1h",
                    "1d": "i18n:enums.interval.1d",
                    "1w": "i18n:enums.interval.1w",
                    "1M": "i18n:enums.interval.1M"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="1d",
                expected_type="str",
            ),
            "adjust": FieldSchema(
                name="adjust",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.adjust",
                description="i18n:fields.OverseasStockHistoricalDataNode.adjust.short",
                help_text="i18n:fields.OverseasStockHistoricalDataNode.adjust.detail",
                default=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CHECKBOX,
            ),
        }

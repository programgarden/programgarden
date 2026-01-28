"""
ProgramGarden Core - Futures Historical Data Node

해외선물 과거 데이터 조회:
- OverseasFuturesHistoricalDataNode: 해외선물 과거 OHLCV 데이터 조회 (CME, EUREX, SGX, HKEX)
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


class OverseasFuturesHistoricalDataNode(BaseNode):
    """
    해외선물 과거 데이터 조회 노드

    해외선물 종목의 과거 OHLCV 데이터를 조회합니다.
    거래소: CME, EUREX, SGX, HKEX
    """

    type: Literal["OverseasFuturesHistoricalDataNode"] = "OverseasFuturesHistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesHistoricalDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/historicaldata_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
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
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.symbols",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.symbols",
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
                help_text="i18n:fields.OverseasFuturesHistoricalDataNode.symbols.help_text",
                object_schema=[
                    {"name": "exchange", "type": "ENUM", "label": "i18n:fields.OverseasFuturesHistoricalDataNode.symbols.exchange", "required": True, "expression_mode": "fixed_only"},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesHistoricalDataNode.symbols.symbol", "required": True, "expression_mode": "fixed_only", "placeholder": "ESH26"},
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
            "start_date": FieldSchema(
                name="start_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.start_date",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.start_date",
                default="{{ months_ago_yyyymmdd(3) }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-01-01",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.OverseasFuturesHistoricalDataNode.start_date.help_text",
            ),
            "end_date": FieldSchema(
                name="end_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.end_date",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.end_date",
                default="{{ today_yyyymmdd() }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-12-31",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.OverseasFuturesHistoricalDataNode.end_date.help_text",
            ),
            "interval": FieldSchema(
                name="interval",
                type=FieldType.ENUM,
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.interval",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.interval",
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
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.adjust",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.adjust.short",
                help_text="i18n:fields.OverseasFuturesHistoricalDataNode.adjust.detail",
                default=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CHECKBOX,
            ),
        }

"""
ProgramGarden Core - Korea Stock Historical Data Node

국내주식 과거 데이터 조회:
- KoreaStockHistoricalDataNode: 국내주식 과거 OHLCV 데이터 조회 (KRX)

Item-based execution:
- Input: 단일 symbol (SplitNode에서 분리된 아이템)
- Output: 단일 value (해당 종목의 과거 OHLCV 데이터)
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
)


class KoreaStockHistoricalDataNode(BaseNode):
    """
    국내주식 과거 데이터 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 과거 OHLCV 데이터를 조회합니다.
    거래소: KRX (KOSPI, KOSDAQ)

    Item-based execution:
    - Input: symbol (단일 종목 {symbol})
    - Output: value (해당 종목의 과거 OHLCV 데이터)
    """

    type: Literal["KoreaStockHistoricalDataNode"] = "KoreaStockHistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.KoreaStockHistoricalDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/historicaldata_korea_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.KOREA_STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution) - 국내주식은 exchange 불필요
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with symbol code (6-digit)",
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
        description="Data interval (1d, 1w, 1M)",
    )
    adjust: bool = Field(
        default=True,
        description="Apply adjusted prices (수정주가 적용)",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="ohlcv_data", description="i18n:ports.ohlcv_value", fields=HISTORICAL_DATA_FIELDS),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.KoreaStockHistoricalDataNode.symbol",
                description="i18n:fields.KoreaStockHistoricalDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"symbol": "005930"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{symbol: str}",
                help_text="i18n:fields.KoreaStockHistoricalDataNode.symbol.help_text",
                object_schema=[
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.KoreaStockHistoricalDataNode.symbol.symbol", "required": True},
                ],
            ),
            "start_date": FieldSchema(
                name="start_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.KoreaStockHistoricalDataNode.start_date",
                description="i18n:fields.KoreaStockHistoricalDataNode.start_date",
                default="{{ months_ago_yyyymmdd(3) }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-01-01",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.KoreaStockHistoricalDataNode.start_date.help_text",
            ),
            "end_date": FieldSchema(
                name="end_date",
                type=FieldType.STRING,
                display_name="i18n:fieldNames.KoreaStockHistoricalDataNode.end_date",
                description="i18n:fields.KoreaStockHistoricalDataNode.end_date",
                default="{{ today_yyyymmdd() }}",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="2024-12-31",
                expected_type="str",
                ui_component=UIComponent.CUSTOM_DATE_PICKER,
                help_text="i18n:fields.KoreaStockHistoricalDataNode.end_date.help_text",
            ),
            "interval": FieldSchema(
                name="interval",
                type=FieldType.ENUM,
                display_name="i18n:fieldNames.KoreaStockHistoricalDataNode.interval",
                description="i18n:fields.KoreaStockHistoricalDataNode.interval",
                default="1d",
                required=True,
                enum_values=["1d", "1w", "1M"],
                enum_labels={
                    "1d": "i18n:enums.interval.1d",
                    "1w": "i18n:enums.interval.1w",
                    "1M": "i18n:enums.interval.1M",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="1d",
                expected_type="str",
            ),
            "adjust": FieldSchema(
                name="adjust",
                type=FieldType.BOOLEAN,
                display_name="i18n:fieldNames.KoreaStockHistoricalDataNode.adjust",
                description="i18n:fields.KoreaStockHistoricalDataNode.adjust.short",
                help_text="i18n:fields.KoreaStockHistoricalDataNode.adjust.detail",
                default=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CHECKBOX,
            ),
        }

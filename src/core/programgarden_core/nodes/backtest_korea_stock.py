"""
ProgramGarden Core - Korea Stock Historical Data Node

국내주식 과거 데이터 조회:
- KoreaStockHistoricalDataNode: 국내주식 과거 OHLCV 데이터 조회 (KRX)

Item-based execution:
- Input: 단일 symbol (SplitNode에서 분리된 아이템)
- Output: 단일 value (해당 종목의 과거 OHLCV 데이터)
"""

from typing import Any, Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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
    _img_url: ClassVar[str] = ""
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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve daily (or weekly/monthly) OHLCV history for a Korean domestic stock (KOSPI/KOSDAQ) for technical analysis or backtesting",
            "Feed historical candles into ConditionNode plugins (RSI, MACD, Bollinger, etc.) for domestic stock strategy evaluation",
            "Use `{{ date.ago(N, format='yyyymmdd') }}` for start_date to maintain a rolling lookback window",
        ],
        "when_not_to_use": [
            "For overseas stock historical data — use OverseasStockHistoricalDataNode",
            "For overseas futures history — use OverseasFuturesHistoricalDataNode",
            "When you only need the current quote snapshot — use KoreaStockMarketDataNode",
        ],
        "typical_scenarios": [
            "SplitNode.item → KoreaStockHistoricalDataNode → ConditionNode (RSI on domestic stock history)",
            "KoreaStockHistoricalDataNode.value → BacktestEngineNode (domestic stock strategy backtest)",
            "KoreaStockHistoricalDataNode.value → LineChartNode (domestic price history chart)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns time_series of OHLCV candles: [{date, open, high, low, close, volume}, ...] ordered oldest-first",
        "Supports intervals: 1d, 1w, 1M — intraday intervals (1m/5m) not available for Korean domestic stocks via this node",
        "adjust=True (default) applies split/dividend-adjusted (수정주가) prices for accurate long-term analysis",
        "start_date / end_date accept YYYYMMDD strings or `{{ date.ago(N, format='yyyymmdd') }}` expressions",
        "is_tool_enabled=True — AI Agent can fetch domestic historical data for fundamental/technical analysis",
        "Symbol format: 6-digit KRX code (e.g., '005930') without exchange field",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Binding `{{ nodes.historical.value }}` directly to ConditionNode data instead of `.time_series`",
            "reason": "The value port is a dict with a `time_series` key — plugins expect a plain list of candle dicts.",
            "alternative": "Bind `{{ nodes.historical.value.time_series }}` to the ConditionNode data field.",
        },
        {
            "pattern": "Using interval='1m' or '5m' for Korean domestic stocks",
            "reason": "Intraday intervals below 1d are not supported for Korean domestic stocks by this node.",
            "alternative": "Use interval='1d' for daily bars. For real-time intraday data, use KoreaStockRealMarketDataNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "60-day daily history for RSI on Samsung Electronics",
            "description": "Fetch 60 days of 005930 daily OHLCV data and compute RSI signal.",
            "workflow_snippet": {
                "id": "korea_stock_historical_rsi",
                "name": "KRX Historical RSI",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "005930"}]},
                    {"id": "historical", "type": "KoreaStockHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(60, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "1d", "adjust": True},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.value.time_series }}", "period": 14, "oversold_threshold": 30},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "historical"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value.time_series: [{date, open, high, low, close, volume}, ...]. RSI ConditionNode emits oversold signal.",
        },
        {
            "title": "Weekly Bollinger Bands on KOSDAQ stock",
            "description": "Fetch 1-year weekly bars for a KOSDAQ stock and apply Bollinger Bands strategy.",
            "workflow_snippet": {
                "id": "korea_stock_historical_bollinger_weekly",
                "name": "KRX Weekly Bollinger",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "KoreaStockBrokerNode", "credential_id": "broker_cred"},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "247540"}]},
                    {"id": "historical", "type": "KoreaStockHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(365, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "1w", "adjust": True},
                    {"id": "condition", "type": "ConditionNode", "plugin": "BollingerBands", "data": "{{ nodes.historical.value.time_series }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "split"},
                    {"from": "split", "to": "historical"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_korea_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Weekly OHLCV in time_series; Bollinger ConditionNode emits upper/lower band breach signal.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single dict with only `symbol` key (6-digit KRX code, e.g., {\"symbol\": \"005930\"}). "
            "No exchange field needed. Supported intervals: 1d, 1w, 1M. "
            "Use adjust=True (default) for accurate long-term analysis with split/dividend-adjusted prices."
        ),
        "output_consumption": (
            "The `value` port emits {symbol, time_series: [{date, open, high, low, close, volume}, ...]}. "
            "Bind `{{ nodes.historical.value.time_series }}` to ConditionNode plugins."
        ),
        "common_combinations": [
            "SplitNode.item → KoreaStockHistoricalDataNode → ConditionNode (technical signal on domestic history)",
            "KoreaStockHistoricalDataNode.value → BacktestEngineNode (domestic stock backtest)",
            "KoreaStockHistoricalDataNode.value → LineChartNode (domestic price history chart)",
        ],
        "pitfalls": [
            "Access time_series via `{{ nodes.historical.value.time_series }}` — the value port wraps the list in a dict",
            "Intraday intervals (1m/5m/15m) not supported for Korean domestic stocks — use 1d minimum",
            "adjust=True is the default; set False only if you specifically need unadjusted prices",
        ],
    }

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

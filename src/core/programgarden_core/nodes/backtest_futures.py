"""
ProgramGarden Core - Futures Historical Data Node

해외선물 과거 데이터 조회:
- OverseasFuturesHistoricalDataNode: 해외선물 과거 OHLCV 데이터 조회 (CME, EUREX, SGX, HKEX)

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


class OverseasFuturesHistoricalDataNode(BaseNode):
    """
    해외선물 과거 데이터 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 과거 OHLCV 데이터를 조회합니다.
    거래소: CME, EUREX, SGX, HKEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 과거 OHLCV 데이터)
    """

    type: Literal["OverseasFuturesHistoricalDataNode"] = "OverseasFuturesHistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesHistoricalDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    # 단일 종목 (Item-based execution)
    symbol: Optional[Dict[str, str]] = Field(
        default=None,
        description="Single symbol entry with exchange and symbol code",
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

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Retrieve daily (or intraday) OHLCV history for an overseas futures contract (CME, EUREX, SGX, HKEX) for technical analysis or backtesting",
            "Feed historical candles into ConditionNode plugins (MACD, Bollinger, etc.) that operate on futures price series",
            "Use `{{ date.ago(N, format='yyyymmdd') }}` for start_date to maintain a rolling lookback window",
        ],
        "when_not_to_use": [
            "For overseas stock historical data — use OverseasStockHistoricalDataNode",
            "For Korean domestic stock history — use KoreaStockHistoricalDataNode",
            "When you only need the current quote snapshot — use OverseasFuturesMarketDataNode",
        ],
        "typical_scenarios": [
            "SplitNode.item → OverseasFuturesHistoricalDataNode → ConditionNode (Bollinger strategy on futures)",
            "OverseasFuturesHistoricalDataNode.value → BacktestEngineNode (futures strategy backtest)",
            "OverseasFuturesHistoricalDataNode.value → BenchmarkCompareNode (performance vs benchmark)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns time_series list of OHLCV candles: [{date, open, high, low, close, volume}, ...] ordered oldest-first",
        "Supports intervals: 1m, 5m, 15m, 1h, 1d, 1w, 1M — daily is the default for swing/position strategies",
        "start_date / end_date accept YYYYMMDD strings or `{{ date.ago(N, format='yyyymmdd') }}` expressions",
        "adjust=True applies roll-adjusted prices for continuous contract backtesting",
        "is_tool_enabled=True — AI Agent can fetch futures history for technical analysis autonomously",
        "Item-based execution: pair with SplitNode to fetch OHLCV for multiple contracts",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Binding `{{ nodes.historical.value }}` directly to ConditionNode data instead of `.time_series`",
            "reason": "The value port is a dict containing a `time_series` key — plugins expect a plain list of candle dicts.",
            "alternative": "Bind `{{ nodes.historical.value.time_series }}` to the ConditionNode data field.",
        },
        {
            "pattern": "Using adjust=False for a continuous contract strategy that spans roll periods",
            "reason": "Unadjusted prices have discontinuities at contract roll dates, which distort momentum and mean-reversion signals.",
            "alternative": "Set adjust=True for strategies that look back across multiple roll periods.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "60-day daily history for Bollinger strategy on E-mini S&P",
            "description": "Fetch 60 days of ESH26 daily OHLCV and compute Bollinger Bands for a mean-reversion signal.",
            "workflow_snippet": {
                "id": "overseas_futures_historical_bollinger",
                "name": "Futures Bollinger Strategy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "ESH26", "exchange": "CME"}]},
                    {"id": "historical", "type": "OverseasFuturesHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(60, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "1d", "adjust": False},
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
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value.time_series: [{date, open, high, low, close, volume}, ...]. ConditionNode computes upper/lower bands and emits signal.",
        },
        {
            "title": "HKEX mini-futures intraday scan",
            "description": "Fetch 1-hour bars for the past 10 days for HKEX mini-futures and apply MACD.",
            "workflow_snippet": {
                "id": "overseas_futures_historical_hkex_macd",
                "name": "HKEX Intraday MACD",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "MHIH26", "exchange": "HKEX"}]},
                    {"id": "historical", "type": "OverseasFuturesHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(10, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "1h", "adjust": False},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.value.time_series }}"},
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
                        "type": "broker_ls_overseas_futures",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "MACD crossover signal computed from 1-hour HKEX mini-futures bars; result port emits buy/sell signal.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict — bind to `{{ nodes.split.item }}` for multi-contract iteration. "
            "Exchange values: CME, EUREX, SGX, HKEX. Symbol includes contract month code (e.g., ESH26). "
            "start_date / end_date: use `{{ date.ago(N, format='yyyymmdd') }}` for rolling lookback. "
            "interval options: 1m, 5m, 15m, 1h, 1d, 1w, 1M."
        ),
        "output_consumption": (
            "The `value` port emits {symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}. "
            "Access via `{{ nodes.historical.value.time_series }}` for ConditionNode plugins."
        ),
        "common_combinations": [
            "SplitNode.item → OverseasFuturesHistoricalDataNode → ConditionNode (technical signal on futures history)",
            "OverseasFuturesHistoricalDataNode.value → BacktestEngineNode (futures backtest)",
            "OverseasFuturesHistoricalDataNode.value → LineChartNode (price history display)",
        ],
        "pitfalls": [
            "Bind `.time_series` not `.value` to ConditionNode data — the value port wraps the list in a dict",
            "Use OverseasFuturesBrokerNode (not OverseasStockBrokerNode) upstream",
            "Contract month codes change every quarter — update symbol (e.g., ESH26 → ESM26) when rolling",
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
                display_name="i18n:fieldNames.OverseasFuturesHistoricalDataNode.symbol",
                description="i18n:fields.OverseasFuturesHistoricalDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "CME", "symbol": "ESH26"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasFuturesHistoricalDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasFuturesHistoricalDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasFuturesHistoricalDataNode.symbol.symbol", "required": True},
                ],
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
                example=True,
            ),
        }

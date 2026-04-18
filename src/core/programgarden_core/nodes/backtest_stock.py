"""
ProgramGarden Core - Stock Historical Data Node

해외주식 과거 데이터 조회:
- OverseasStockHistoricalDataNode: 해외주식 과거 OHLCV 데이터 조회 (NYSE, NASDAQ, AMEX)

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


class OverseasStockHistoricalDataNode(BaseNode):
    """
    해외주식 과거 데이터 조회 노드 (단일 종목)

    SplitNode와 함께 사용하여 개별 종목의 과거 OHLCV 데이터를 조회합니다.
    거래소: NYSE, NASDAQ, AMEX

    Item-based execution:
    - Input: symbol (단일 종목 {exchange, symbol})
    - Output: value (해당 종목의 과거 OHLCV 데이터)
    """

    type: Literal["OverseasStockHistoricalDataNode"] = "OverseasStockHistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasStockHistoricalDataNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
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
            "Retrieve daily (or intraday) OHLCV history for a US-listed stock to compute technical indicators or run backtests",
            "Feed time-series data into ConditionNode plugins (RSI, MACD, Bollinger, etc.) that require a `data` list of candles",
            "Use `{{ date.ago(N, format='yyyymmdd') }}` for start_date to get a rolling lookback window without hardcoding dates",
        ],
        "when_not_to_use": [
            "For overseas futures historical data — use OverseasFuturesHistoricalDataNode",
            "For Korean domestic stock history — use KoreaStockHistoricalDataNode",
            "When you only need the latest quote snapshot — use OverseasStockMarketDataNode",
        ],
        "typical_scenarios": [
            "SplitNode.item → OverseasStockHistoricalDataNode → ConditionNode (RSI/MACD on time-series)",
            "OverseasStockHistoricalDataNode.value → BacktestEngineNode (strategy backtesting)",
            "WatchlistNode → SplitNode → OverseasStockHistoricalDataNode → ConditionNode → OverseasStockNewOrderNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Returns a list of OHLCV candles in `value.time_series`: [{date, open, high, low, close, volume}, ...]",
        "Supports intervals: 1m, 5m, 15m, 1h, 1d, 1w, 1M — daily (1d) is the default for swing trading strategies",
        "start_date / end_date accept YYYYMMDD strings or expression namespace calls: `{{ date.ago(30, format='yyyymmdd') }}`",
        "adjust=True applies split/dividend-adjusted prices for accurate long-term backtesting",
        "is_tool_enabled=True — AI Agent can fetch historical data autonomously for technical analysis",
        "Item-based execution: pair with SplitNode to fetch history for each symbol in a watchlist",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using a fixed hardcoded start_date string like '20200101' without using the date namespace",
            "reason": "The lookback window becomes stale over time and will fetch unnecessarily large datasets as time passes.",
            "alternative": "Use `{{ date.ago(90, format='yyyymmdd') }}` for a rolling 90-day window that stays current.",
        },
        {
            "pattern": "Binding the full value output to a ConditionNode `data` field without accessing `.time_series`",
            "reason": "Most plugins expect a flat list of OHLCV dicts. The value port is a dict with a `time_series` key.",
            "alternative": "Bind `{{ nodes.historical.value.time_series }}` to the ConditionNode's data field.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "30-day daily history for RSI signal",
            "description": "Fetch 30 days of AAPL daily OHLCV data and pass the time_series to RSI ConditionNode.",
            "workflow_snippet": {
                "id": "overseas_stock_historical_rsi",
                "name": "Historical RSI Signal",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(30, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "1d", "adjust": False},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value port: {symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}. RSI is computed from time_series.",
        },
        {
            "title": "Intraday 5-minute data for MACD",
            "description": "Fetch 5-minute bars over the past 5 days for MSFT and compute MACD crossover signal.",
            "workflow_snippet": {
                "id": "overseas_stock_historical_macd_5m",
                "name": "Intraday MACD",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "split", "type": "SplitNode", "items": [{"symbol": "MSFT", "exchange": "NASDAQ"}]},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbol": "{{ nodes.split.item }}", "start_date": "{{ date.ago(5, format='yyyymmdd') }}", "end_date": "{{ date.today(format='yyyymmdd') }}", "interval": "5m", "adjust": False},
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
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "value.time_series contains 5-minute OHLCV bars; MACD ConditionNode emits signal/histogram on the result port.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": (
            "The `symbol` field takes a single {exchange, symbol} dict — bind to `{{ nodes.split.item }}` in a per-symbol loop. "
            "start_date / end_date accept 'YYYYMMDD' strings or `{{ date.ago(N, format='yyyymmdd') }}` expressions. "
            "interval options: 1m, 5m, 15m, 1h, 1d, 1w, 1M. Use adjust=True for long-term backtesting to remove split/dividend distortions."
        ),
        "output_consumption": (
            "The `value` port emits a dict: {symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}. "
            "Bind `{{ nodes.historical.value.time_series }}` to ConditionNode's `data` field. "
            "The list is ordered oldest-first (ascending by date)."
        ),
        "common_combinations": [
            "SplitNode.item → OverseasStockHistoricalDataNode → ConditionNode (technical indicator on history)",
            "OverseasStockHistoricalDataNode.value → BacktestEngineNode (strategy simulation)",
            "OverseasStockHistoricalDataNode.value → BenchmarkCompareNode (benchmark comparison)",
            "OverseasStockHistoricalDataNode.value → LineChartNode (price chart display)",
        ],
        "pitfalls": [
            "Access time_series via `{{ nodes.historical.value.time_series }}` — the value port is a dict, not a plain list",
            "Intraday intervals (1m/5m/15m/1h) may have limited history depth depending on LS Securities API availability",
            "adjust=False (default) returns unadjusted prices; set True when comparing long-term price levels across splits",
            "Large date ranges with 1m interval can return thousands of rows — set reasonable start_date to avoid memory pressure",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(name="symbol", type="symbol", description="i18n:ports.symbol"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="value",
            type="ohlcv_data",
            description="i18n:ports.ohlcv_value",
            fields=HISTORICAL_DATA_FIELDS,
            example=[
                {
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "time_series": [
                        {"date": "20260413", "open": 186.10, "high": 188.20, "low": 185.50, "close": 187.45, "volume": 12_345_678},
                        {"date": "20260412", "open": 184.50, "high": 187.00, "low": 184.00, "close": 186.10, "volume": 11_222_333},
                    ],
                },
            ],
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "symbol": FieldSchema(
                name="symbol",
                type=FieldType.OBJECT,
                display_name="i18n:fieldNames.OverseasStockHistoricalDataNode.symbol",
                description="i18n:fields.OverseasStockHistoricalDataNode.symbol",
                default=None,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example={"exchange": "NASDAQ", "symbol": "AAPL"},
                example_binding="{{ nodes.split.item }}",
                bindable_sources=[
                    "SplitNode.item",
                ],
                expected_type="{exchange: str, symbol: str}",
                help_text="i18n:fields.OverseasStockHistoricalDataNode.symbol.help_text",
                object_schema=[
                    {"name": "exchange", "type": "STRING", "label": "i18n:fields.OverseasStockHistoricalDataNode.symbol.exchange", "required": True},
                    {"name": "symbol", "type": "STRING", "label": "i18n:fields.OverseasStockHistoricalDataNode.symbol.symbol", "required": True},
                ],
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
                example=True,
            ),
        }

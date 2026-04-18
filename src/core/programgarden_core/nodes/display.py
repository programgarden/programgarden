"""
ProgramGarden Core - Display Nodes

차트/테이블/요약 시각화 노드 (6개)
- TableDisplayNode: 테이블/그리드 표시
- LineChartNode: 단일 라인 차트
- MultiLineChartNode: 다중 시리즈 라인 차트
- CandlestickChartNode: OHLCV 캔들스틱 차트
- BarChartNode: 막대 차트
- SummaryDisplayNode: JSON/요약 데이터 표시
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


# ── OutputPort.fields 상수 (Display 노드용) ──

TABLE_DISPLAY_FIELDS: List[Dict[str, Any]] = [
    {"name": "columns", "type": "dynamic", "description": "표시할 컬럼 (설정에 따라 결정)"},
]

LINE_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

MULTI_LINE_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
    {"name": "series_key", "type": "dynamic", "description": "시리즈 구분 키 (series_key로 지정)"},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

CANDLESTICK_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "date", "type": "dynamic", "description": "날짜 (date_field로 지정)"},
    {"name": "open", "type": "number", "description": "시가 (open_field로 지정)"},
    {"name": "high", "type": "number", "description": "고가 (high_field로 지정)"},
    {"name": "low", "type": "number", "description": "저가 (low_field로 지정)"},
    {"name": "close", "type": "number", "description": "종가 (close_field로 지정)"},
    {"name": "volume", "type": "number", "description": "거래량 (volume_field로 지정)", "nullable": True},
    {"name": "signal", "type": "string", "description": "매매 시그널 (buy/sell)", "nullable": True},
    {"name": "side", "type": "string", "description": "포지션 방향 (long/short)", "nullable": True},
]

BAR_CHART_FIELDS: List[Dict[str, Any]] = [
    {"name": "x", "type": "dynamic", "description": "X축 값 (x_field로 지정)"},
    {"name": "y", "type": "dynamic", "description": "Y축 값 (y_field로 지정)"},
]

SUMMARY_DISPLAY_FIELDS: List[Dict[str, Any]] = [
    {"name": "data", "type": "any", "description": "요약 데이터 (JSON 객체 또는 원시값)"},
]


# ── 공통 data_schema 필드 ──

_SIGNAL_FIELD = {
    "type": "string",
    "resolved_by": "signal_field",
    "nullable": True,
    "enum": ["buy", "sell"],
    "description": "i18n:display_schema.common.signal",
}

_SIDE_FIELD = {
    "type": "string",
    "resolved_by": "side_field",
    "nullable": True,
    "enum": ["long", "short"],
    "description": "i18n:display_schema.common.side",
}


class BaseDisplayNode(BaseNode):
    """Display 노드 공통 베이스"""

    category: NodeCategory = NodeCategory.DISPLAY

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = None

    title: Optional[str] = Field(
        default=None,
        description="차트 제목",
    )

    data: Any = Field(
        default=None,
        description="데이터 바인딩 (예: {{ nodes.condition.values }})",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data",
            required=False,
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="rendered",
            type="signal",
            description="렌더링 완료 신호",
        ),
    ]

    @classmethod
    def _common_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """공통 필드 스키마 (title, data)"""
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            "title": FieldSchema(
                name="title",
                type=FieldType.STRING,
                description="차트 제목",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="데이터 바인딩",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example_binding="{{ nodes.condition.values }}",
                bindable_sources=[
                    "ConditionNode.values",
                    "HistoricalDataNode.values",
                    "BacktestEngineNode.equity_curve",
                    "BacktestEngineNode.summary",
                    "RealAccountNode.positions",
                    "RealMarketDataNode.data",
                ],
            ),
        }


class TableDisplayNode(BaseDisplayNode):
    """테이블/그리드 형태로 데이터를 표시"""

    type: Literal["TableDisplayNode"] = "TableDisplayNode"
    description: str = "i18n:nodes.TableDisplayNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Display a list of records (positions, quotes, signals, backtest trades) as a grid in the workflow UI",
            "Show AI Agent output as a structured table when output_format is 'json' or 'structured'",
            "Present filtered or sorted data sets at the end of a workflow for human review",
        ],
        "when_not_to_use": [
            "For time-series visualization — use LineChartNode or CandlestickChartNode instead",
            "For single-value or key-value summaries — use SummaryDisplayNode instead",
            "For comparing multiple strategies over time — use MultiLineChartNode",
        ],
        "typical_scenarios": [
            "OverseasStockAccountNode → TableDisplayNode (display current positions)",
            "ConditionNode → TableDisplayNode (show RSI signals per symbol)",
            "AIAgentNode → TableDisplayNode (show structured risk analysis table)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Accepts any list[dict] data source via expression binding or data input port",
        "Configurable columns (subset/order), row limit (1-100), and sort_by/sort_order options",
        "Emits on_display_data events consumed by the workflow UI renderer",
        "Optional title field displayed as the table header in the UI",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Binding a single dict (not a list) to TableDisplayNode data",
            "reason": "TableDisplayNode expects list[dict]. A plain dict renders as a single-column table with keys, which is rarely useful.",
            "alternative": "Wrap single records in a list ([{{ nodes.market.value }}]) or use SummaryDisplayNode for single-object display.",
        },
        {
            "pattern": "Setting limit=100 for a live dashboard that updates every second",
            "reason": "Rendering 100 rows on every real-time tick floods the UI with events and degrades performance.",
            "alternative": "Keep limit at 10-20 for live dashboards. Use ThrottleNode upstream for real-time sources.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display current account positions as a table",
            "description": "Fetch overseas stock positions and render them as a sortable table showing symbol, quantity, and P&L.",
            "workflow_snippet": {
                "id": "table_positions",
                "name": "Positions Table",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "table", "type": "TableDisplayNode", "title": "Current Positions", "data": "{{ nodes.account.positions }}", "columns": ["symbol", "exchange", "quantity", "avg_price", "pnl"], "sort_by": "pnl", "sort_order": "desc", "limit": 20},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "table"},
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
            "expected_output": "A table of positions sorted by P&L descending, showing up to 20 rows.",
        },
        {
            "title": "Show RSI signals for a symbol watchlist",
            "description": "Run RSI on historical data for multiple symbols and display the resulting signals in a table.",
            "workflow_snippet": {
                "id": "table_rsi_signals",
                "name": "RSI Signal Table",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}], "period": "1m", "count": 60},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {"id": "table", "type": "TableDisplayNode", "title": "RSI Signals", "data": "{{ nodes.condition.values }}", "limit": 10},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "table"},
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
            "expected_output": "A table showing symbol, RSI value, and signal for each of the analyzed symbols.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to any list[dict] output from upstream nodes using an expression (e.g. {{ nodes.account.positions }}). The 'trigger' input port is optional and can be used when you want to delay rendering until a signal arrives.",
        "output_consumption": "'rendered' signal port fires after the table is emitted. Chain it to subsequent nodes if you need sequential execution after display. The actual table data arrives via on_display_data callback to the UI listener.",
        "common_combinations": [
            "OverseasStockAccountNode → TableDisplayNode (positions dashboard)",
            "ConditionNode → TableDisplayNode (signal list)",
            "AIAgentNode → TableDisplayNode (structured analysis result)",
        ],
        "pitfalls": [
            "TableDisplayNode does not persist data — it only emits display events. Use SQLiteNode to store data for later.",
            "columns list controls display order but NOT which fields are fetched. All fields are still passed to the renderer.",
            "If data is None or empty, the table renders as empty without errors — add a ConditionNode guard if empty data should halt execution.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=TABLE_DISPLAY_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.table.description",
        "items": {
            "type": "object",
            "properties": {
                "columns": {
                    "type": "dynamic",
                    "resolved_by": "columns",
                    "description": "i18n:display_schema.table.columns",
                },
            },
            "required": [],
        },
        "options_fields": ["columns", "limit", "sort_by", "sort_order"],
    }

    columns: Optional[List[str]] = Field(
        default=None,
        description="표시할 컬럼 목록 (미지정시 전체)",
    )

    limit: Optional[int] = Field(
        default=10,
        description="최대 표시 개수",
        ge=1,
        le=100,
    )

    sort_by: Optional[str] = Field(
        default=None,
        description="정렬 기준 필드",
    )

    sort_order: Optional[Literal["asc", "desc"]] = Field(
        default="desc",
        description="정렬 순서",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "columns": FieldSchema(
                name="columns",
                type=FieldType.ARRAY,
                description="표시할 컬럼 목록",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_options={"multiple": True},
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.INTEGER,
                description="최대 표시 개수",
                default=10,
                min_value=1,
                max_value=100,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_by": FieldSchema(
                name="sort_by",
                type=FieldType.STRING,
                description="정렬 기준 필드",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_order": FieldSchema(
                name="sort_order",
                type=FieldType.ENUM,
                description="정렬 순서",
                enum_values=["asc", "desc"],
                default="desc",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        })
        return schema


class LineChartNode(BaseDisplayNode):
    """시계열 라인 차트"""

    type: Literal["LineChartNode"] = "LineChartNode"
    description: str = "i18n:nodes.LineChartNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Plot a single time-series metric over time (RSI, equity curve, price, portfolio value)",
            "Visualize backtest equity curve from BacktestEngineNode on a date axis",
            "Display a strategy indicator (MACD, Bollinger Band midline) with optional buy/sell markers",
        ],
        "when_not_to_use": [
            "For multiple overlapping series (e.g. comparing RSI for 5 symbols) — use MultiLineChartNode instead",
            "For OHLCV candlestick data — use CandlestickChartNode instead",
            "For categorical (non-time) x-axis data — use BarChartNode instead",
        ],
        "typical_scenarios": [
            "BacktestEngineNode → LineChartNode (equity_curve, x=date, y=equity)",
            "ConditionNode → LineChartNode (values, x=date, y=rsi, signal_field=signal)",
            "OverseasStockHistoricalDataNode → LineChartNode (values, x=date, y=close)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Configurable x_field and y_field to map any date/value columns from the data source",
        "Optional signal_field and side_field overlay buy/sell markers and long/short shading on the chart",
        "Emits on_display_data callback for real-time rendering in the workflow UI",
        "Optional title field shown as the chart heading",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using LineChartNode without setting x_field and y_field",
            "reason": "Without field names the renderer cannot identify which column to plot, resulting in an empty chart.",
            "alternative": "Always specify x_field (e.g. 'date') and y_field (e.g. 'rsi' or 'equity') matching actual keys in the data.",
        },
        {
            "pattern": "Feeding raw OHLCV list to LineChartNode expecting a candlestick view",
            "reason": "LineChartNode renders a single y-value per x-point. OHLCV data requires CandlestickChartNode for proper candlestick rendering.",
            "alternative": "Use CandlestickChartNode with date_field, open_field, high_field, low_field, close_field.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Plot RSI values over time with buy/sell markers",
            "description": "Feed ConditionNode RSI output to LineChartNode. The signal_field='signal' overlays buy/sell triangle markers on the RSI line.",
            "workflow_snippet": {
                "id": "linechart_rsi",
                "name": "RSI Line Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1m", "count": 120},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {"id": "chart", "type": "LineChartNode", "title": "AAPL RSI (14)", "data": "{{ nodes.condition.values }}", "x_field": "date", "y_field": "rsi", "signal_field": "signal"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "chart"},
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
            "expected_output": "A rendered RSI line chart for AAPL with buy/sell markers at oversold/overbought crossings.",
        },
        {
            "title": "Visualize backtest equity curve",
            "description": "Connect BacktestEngineNode equity_curve to LineChartNode to show portfolio growth over the backtest period.",
            "workflow_snippet": {
                "id": "linechart_equity",
                "name": "Equity Curve Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {"id": "backtest", "type": "BacktestEngineNode", "initial_capital": 10000, "commission_rate": 0.001, "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "SPY", "exchange": "NYSE", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}}},
                    {"id": "chart", "type": "LineChartNode", "title": "Strategy Equity Curve", "data": "{{ nodes.backtest.equity_curve }}", "x_field": "date", "y_field": "equity"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "backtest"},
                    {"from": "backtest", "to": "chart"},
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
            "expected_output": "A line chart showing portfolio equity growing (or declining) from initial_capital=10000 over the 252-day period.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to a list[dict] where each dict has the x_field and y_field keys. If data is pre-sorted by date, the chart renders in chronological order. If not sorted, the UI renderer typically sorts by x_field automatically.",
        "output_consumption": "'rendered' signal fires after the chart event is emitted. Chain it only if you need sequential execution. The actual chart data is consumed by the on_display_data listener in the UI layer.",
        "common_combinations": [
            "ConditionNode → LineChartNode (indicator time series with signal markers)",
            "BacktestEngineNode → LineChartNode (equity curve visualization)",
            "OverseasStockHistoricalDataNode → LineChartNode (raw price line chart)",
        ],
        "pitfalls": [
            "x_field and y_field must exactly match the key names in the data — a typo causes a blank chart without an error.",
            "LineChartNode renders a single series. If the data list contains entries for multiple symbols, all points are plotted on the same axis without differentiation.",
            "signal_field expects 'buy' or 'sell' string values in the data. Any other values are ignored by the marker renderer.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=LINE_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.line.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "date",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "rsi",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["x", "y"],
        },
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명 (예: date)",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명 (예: rsi)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="rsi",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
        })
        return schema


class MultiLineChartNode(BaseDisplayNode):
    """다중 시리즈 라인 차트"""

    type: Literal["MultiLineChartNode"] = "MultiLineChartNode"
    description: str = "i18n:nodes.MultiLineChartNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compare the same metric across multiple symbols on a single chart (e.g. RSI for AAPL, MSFT, NVDA)",
            "Overlay strategy equity curves from BenchmarkCompareNode for side-by-side comparison",
            "Visualize multi-symbol historical prices or portfolio weights over time in one view",
        ],
        "when_not_to_use": [
            "For a single symbol/series — use LineChartNode which is simpler and has the same rendering quality",
            "For OHLCV candlestick data — use CandlestickChartNode",
            "For categorical bar comparisons — use BarChartNode",
        ],
        "typical_scenarios": [
            "BenchmarkCompareNode → MultiLineChartNode (combined_curve, x=date, y=equity, series_key=strategy_name)",
            "ConditionNode (multi-symbol RSI) → MultiLineChartNode (x=date, y=rsi, series_key=symbol)",
            "OverseasStockHistoricalDataNode (multiple symbols) → MultiLineChartNode (x=date, y=close, series_key=symbol)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Mandatory series_key field groups data rows into separate colored lines per unique value",
        "Supports optional signal_field and side_field overlays for buy/sell markers per series",
        "Configurable limit, sort_by, and sort_order to control which rows are displayed",
        "Accepts any list[dict] where each row has the x, y, and series_key fields",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Not setting series_key, resulting in all data points on a single undifferentiated line",
            "reason": "Without series_key the chart cannot separate rows into distinct series. All points merge into one line.",
            "alternative": "Always set series_key to the field name that uniquely identifies each series (e.g. 'symbol', 'strategy_name').",
        },
        {
            "pattern": "Using MultiLineChartNode with data that has inconsistent x-axis values across series",
            "reason": "If Series A has dates [Jan, Feb, Mar] and Series B has [Feb, Mar, Apr], the chart alignment may look incorrect.",
            "alternative": "Ensure all series share the same x-axis values. Use AggregateNode or FieldMappingNode to align data before charting.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Compare RSI across multiple symbols",
            "description": "ConditionNode outputs RSI for several symbols. MultiLineChartNode groups them by 'symbol' to render one RSI line per symbol.",
            "workflow_snippet": {
                "id": "multiline_rsi_compare",
                "name": "Multi-Symbol RSI Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}], "period": "1m", "count": 60},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {"id": "chart", "type": "MultiLineChartNode", "title": "RSI Comparison", "data": "{{ nodes.condition.values }}", "x_field": "date", "y_field": "rsi", "series_key": "symbol"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "chart"},
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
            "expected_output": "A multi-line chart with one RSI line for AAPL and one for MSFT, plotted on the same date axis.",
        },
        {
            "title": "Compare strategy equity curves side by side",
            "description": "BenchmarkCompareNode produces a combined_curve where each row has strategy_name, date, and equity. MultiLineChartNode separates them into colored lines.",
            "workflow_snippet": {
                "id": "multiline_equity_compare",
                "name": "Strategy Equity Comparison",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {"id": "backtest", "type": "BacktestEngineNode", "initial_capital": 10000, "commission_rate": 0.001, "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "SPY", "exchange": "NYSE", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}}},
                    {"id": "benchmark", "type": "BenchmarkCompareNode", "strategies": "{{ nodes.backtest.equity_curve }}"},
                    {"id": "chart", "type": "MultiLineChartNode", "title": "Strategy vs Benchmark", "data": "{{ nodes.benchmark.combined_curve }}", "x_field": "date", "y_field": "equity", "series_key": "strategy_name"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "backtest"},
                    {"from": "backtest", "to": "benchmark"},
                    {"from": "benchmark", "to": "chart"},
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
            "expected_output": "A multi-line chart showing equity curves for the MACD strategy and the buy-and-hold benchmark on the same date axis.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to a list[dict] where each row has x_field, y_field, and series_key columns. All three field names must be set before the chart can render. The data can come from any node that outputs a list with consistent columns.",
        "output_consumption": "'rendered' signal fires after the chart event is emitted. The actual chart appears in the on_display_data callback received by the UI listener.",
        "common_combinations": [
            "BenchmarkCompareNode → MultiLineChartNode (combined equity curves)",
            "ConditionNode (multi-symbol output) → MultiLineChartNode (per-symbol indicator lines)",
            "OverseasStockHistoricalDataNode → MultiLineChartNode (price comparison)",
        ],
        "pitfalls": [
            "series_key is required — omitting it makes all rows appear on a single unnamed line.",
            "Limit applies after all series are combined. If limit=10 and you have 3 series with 20 rows each, only 10 total rows are shown, potentially cutting series short.",
            "Data must contain consistent x-axis values across series for a meaningful comparison chart.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=MULTI_LINE_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.multi_line.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "date",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "rsi",
                },
                "series_key": {
                    "type": "dynamic",
                    "resolved_by": "series_key",
                    "description": "i18n:display_schema.multi_line.series_key",
                    "example": "symbol",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["x", "y", "series_key"],
        },
        "options_fields": ["limit", "sort_by", "sort_order"],
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명 (예: date)",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명 (예: rsi)",
    )

    series_key: Optional[str] = Field(
        default=None,
        description="시리즈 구분 키 (예: symbol)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
    )

    limit: Optional[int] = Field(
        default=10,
        description="최대 표시 개수",
        ge=1,
        le=100,
    )

    sort_by: Optional[str] = Field(
        default=None,
        description="정렬 기준 필드",
    )

    sort_order: Optional[Literal["asc", "desc"]] = Field(
        default="desc",
        description="정렬 순서",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="rsi",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "series_key": FieldSchema(
                name="series_key",
                type=FieldType.STRING,
                description="시리즈 구분 키 (심볼별 라인)",
                placeholder="symbol",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.INTEGER,
                description="최대 표시 개수",
                default=10,
                min_value=1,
                max_value=100,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_by": FieldSchema(
                name="sort_by",
                type=FieldType.STRING,
                description="정렬 기준 필드",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "sort_order": FieldSchema(
                name="sort_order",
                type=FieldType.ENUM,
                description="정렬 순서",
                enum_values=["asc", "desc"],
                default="desc",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        })
        return schema


class CandlestickChartNode(BaseDisplayNode):
    """OHLCV 캔들스틱 차트"""

    type: Literal["CandlestickChartNode"] = "CandlestickChartNode"
    description: str = "i18n:nodes.CandlestickChartNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Visualize OHLCV price history for technical analysis directly in the workflow UI",
            "Display historical candlestick data with buy/sell signal markers from ConditionNode output",
            "Show a backtest result overlaid on the original candlestick chart for strategy review",
        ],
        "when_not_to_use": [
            "For non-OHLCV time-series (RSI, MACD values) — use LineChartNode instead",
            "For comparing multiple assets — CandlestickChartNode renders a single symbol. Use MultiLineChartNode for comparison",
            "For category-based comparisons — use BarChartNode",
        ],
        "typical_scenarios": [
            "OverseasStockHistoricalDataNode → CandlestickChartNode (date_field=date, open_field=open, ...)",
            "ConditionNode → CandlestickChartNode (with signal_field to mark buy/sell on candles)",
            "BacktestEngineNode (trades output) → CandlestickChartNode (overlay trade entry/exit points)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Renders standard OHLCV candlesticks: open, high, low, close, optional volume",
        "Optional signal_field and side_field overlay buy/sell markers and position direction shading on candles",
        "All OHLCV field names are configurable to match any data source column naming convention",
        "Emits on_display_data event for real-time rendering in the workflow UI",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Feeding non-OHLCV data (e.g. RSI values list) to CandlestickChartNode",
            "reason": "CandlestickChartNode requires open/high/low/close fields. If any required field is missing, candles cannot be rendered.",
            "alternative": "Use LineChartNode for single-value indicators. Only use CandlestickChartNode with historical price data.",
        },
        {
            "pattern": "Setting all _field names (open_field, high_field etc.) to the same value",
            "reason": "Each field name must map to a distinct column in the data. Mapping all to 'close' produces flat, meaningless candles.",
            "alternative": "Verify the data schema from HistoricalDataNode first (typically date, open, high, low, close, volume) and map accordingly.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display OHLCV candlestick chart for a single symbol",
            "description": "Fetch 60 days of historical data for NVDA and render a standard candlestick chart.",
            "workflow_snippet": {
                "id": "candlestick_basic",
                "name": "NVDA Candlestick Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "NVDA", "exchange": "NASDAQ"}], "period": "1d", "count": 60},
                    {
                        "id": "chart",
                        "type": "CandlestickChartNode",
                        "title": "NVDA 60-Day Candles",
                        "data": "{{ nodes.historical.values }}",
                        "date_field": "date",
                        "open_field": "open",
                        "high_field": "high",
                        "low_field": "low",
                        "close_field": "close",
                        "volume_field": "volume",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "chart"},
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
            "expected_output": "A candlestick chart showing 60 daily OHLCV candles for NVDA with volume subplot.",
        },
        {
            "title": "Candlestick chart with RSI buy/sell signal markers",
            "description": "Overlay RSI signal markers on the candlestick chart so entry/exit points are visible on the price chart.",
            "workflow_snippet": {
                "id": "candlestick_signals",
                "name": "Candlestick with RSI Signals",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1d", "count": 90},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {
                        "id": "chart",
                        "type": "CandlestickChartNode",
                        "title": "AAPL with RSI Signals",
                        "data": "{{ nodes.condition.values }}",
                        "date_field": "date",
                        "open_field": "open",
                        "high_field": "high",
                        "low_field": "low",
                        "close_field": "close",
                        "volume_field": "volume",
                        "signal_field": "signal",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "chart"},
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
            "expected_output": "A candlestick chart for AAPL with green arrow markers at RSI buy signals and red arrows at sell signals.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to a list[dict] with OHLCV keys. Set date_field, open_field, high_field, low_field, and close_field to match the actual column names in the data. volume_field is optional. signal_field expects 'buy'/'sell' string values.",
        "output_consumption": "'rendered' signal fires after the chart event is emitted. The actual candlestick data is delivered via on_display_data to the UI layer. No further data transformation happens after this node.",
        "common_combinations": [
            "OverseasStockHistoricalDataNode → CandlestickChartNode",
            "ConditionNode → CandlestickChartNode (with signal overlay)",
            "BacktestEngineNode.trades → CandlestickChartNode (with signal_field=action)",
        ],
        "pitfalls": [
            "date_field, open_field, high_field, low_field, and close_field are all required — omitting any one leaves the chart unrenderable.",
            "Feeding intraday tick data with thousands of rows causes rendering performance issues. Aggregate or limit to 500 candles maximum.",
            "signal_field values other than 'buy' or 'sell' are silently ignored by the marker renderer.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=CANDLESTICK_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.candlestick.description",
        "items": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "dynamic",
                    "resolved_by": "date_field",
                    "description": "i18n:display_schema.candlestick.date",
                    "example": "date",
                },
                "open": {
                    "type": "number",
                    "resolved_by": "open_field",
                    "description": "i18n:display_schema.candlestick.open",
                    "example": "open",
                },
                "high": {
                    "type": "number",
                    "resolved_by": "high_field",
                    "description": "i18n:display_schema.candlestick.high",
                    "example": "high",
                },
                "low": {
                    "type": "number",
                    "resolved_by": "low_field",
                    "description": "i18n:display_schema.candlestick.low",
                    "example": "low",
                },
                "close": {
                    "type": "number",
                    "resolved_by": "close_field",
                    "description": "i18n:display_schema.candlestick.close",
                    "example": "close",
                },
                "volume": {
                    "type": "number",
                    "resolved_by": "volume_field",
                    "nullable": True,
                    "description": "i18n:display_schema.candlestick.volume",
                    "example": "volume",
                },
                "signal": _SIGNAL_FIELD,
                "side": _SIDE_FIELD,
            },
            "required": ["date", "open", "high", "low", "close"],
        },
    }

    date_field: Optional[str] = Field(
        default=None,
        description="날짜 필드명",
    )

    open_field: Optional[str] = Field(
        default=None,
        description="시가 필드명",
    )

    high_field: Optional[str] = Field(
        default=None,
        description="고가 필드명",
    )

    low_field: Optional[str] = Field(
        default=None,
        description="저가 필드명",
    )

    close_field: Optional[str] = Field(
        default=None,
        description="종가 필드명",
    )

    volume_field: Optional[str] = Field(
        default=None,
        description="거래량 필드명 (선택)",
    )

    signal_field: Optional[str] = Field(
        default=None,
        description="시그널 필드명 (buy/sell 마커 표시)",
    )

    side_field: Optional[str] = Field(
        default=None,
        description="포지션 방향 필드명 (long/short 구분)",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="날짜 필드명",
                placeholder="date",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="시가 필드명",
                placeholder="open",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="고가 필드명",
                placeholder="high",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="저가 필드명",
                placeholder="low",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="종가 필드명",
                placeholder="close",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="거래량 필드명 (선택)",
                placeholder="volume",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="시그널 필드명 (buy/sell 마커 표시)",
                placeholder="signal",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="포지션 방향 필드명 (long/short 구분)",
                placeholder="side",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                group="field_mapping",
            ),
        })
        return schema


class BarChartNode(BaseDisplayNode):
    """막대 차트"""

    type: Literal["BarChartNode"] = "BarChartNode"
    description: str = "i18n:nodes.BarChartNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compare a single metric across discrete categories (e.g. total P&L per symbol, sector allocation %)",
            "Display backtest ranking metrics from BenchmarkCompareNode as a bar comparison",
            "Show portfolio weight or exposure breakdown by symbol or sector",
        ],
        "when_not_to_use": [
            "For time-series data with a continuous date axis — use LineChartNode or CandlestickChartNode instead",
            "For comparing multiple metrics on the same category — use MultiLineChartNode or a custom SummaryDisplayNode",
            "For OHLCV data — use CandlestickChartNode",
        ],
        "typical_scenarios": [
            "OverseasStockAccountNode → BarChartNode (x=symbol, y=pnl — P&L per position)",
            "BenchmarkCompareNode → BarChartNode (x=strategy_name, y=sharpe — Sharpe ratio comparison)",
            "ConditionNode → BarChartNode (x=symbol, y=rsi — current RSI snapshot across symbols)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Configurable x_field (category axis) and y_field (value axis) map to any list[dict] columns",
        "Renders horizontal or vertical bars depending on UI settings",
        "Emits on_display_data callback for real-time rendering in the workflow UI",
        "Optional title field displayed as the chart heading",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using BarChartNode with a continuous date x-axis for time-series data",
            "reason": "Bar charts with many date categories become unreadable. Time-series data belongs on a LineChartNode.",
            "alternative": "Use LineChartNode for date-based x-axis data. Reserve BarChartNode for categorical comparisons.",
        },
        {
            "pattern": "Not setting x_field and y_field, leaving them as None",
            "reason": "Without field names the chart renderer cannot identify which columns to plot, producing an empty chart.",
            "alternative": "Always set x_field (e.g. 'symbol') and y_field (e.g. 'pnl') matching actual keys in the data.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "P&L bar chart for current positions",
            "description": "Fetch account positions and display a bar chart showing P&L per symbol, sorted by value.",
            "workflow_snippet": {
                "id": "barchart_pnl",
                "name": "P&L Bar Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "chart", "type": "BarChartNode", "title": "P&L by Symbol", "data": "{{ nodes.account.positions }}", "x_field": "symbol", "y_field": "pnl"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "chart"},
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
            "expected_output": "A bar chart with one bar per position symbol, height proportional to P&L (positive=green, negative=red).",
        },
        {
            "title": "Sharpe ratio comparison across backtest strategies",
            "description": "BenchmarkCompareNode outputs comparison_metrics with strategy_name and sharpe. BarChartNode renders one bar per strategy.",
            "workflow_snippet": {
                "id": "barchart_sharpe",
                "name": "Sharpe Ratio Comparison",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {"id": "backtest", "type": "BacktestEngineNode", "initial_capital": 10000, "commission_rate": 0.001, "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "SPY", "exchange": "NYSE", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}}},
                    {"id": "benchmark", "type": "BenchmarkCompareNode", "strategies": "{{ nodes.backtest.equity_curve }}"},
                    {"id": "chart", "type": "BarChartNode", "title": "Sharpe Ratio by Strategy", "data": "{{ nodes.benchmark.comparison_metrics }}", "x_field": "strategy_name", "y_field": "sharpe"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "backtest"},
                    {"from": "backtest", "to": "benchmark"},
                    {"from": "benchmark", "to": "chart"},
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
            "expected_output": "A bar chart with one bar per strategy showing their relative Sharpe ratios for easy comparison.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to a list[dict] where each dict has x_field and y_field keys. The node renders one bar per row. Sorting or filtering should be done upstream (TableDisplayNode sort_by or ConditionNode filter logic) before reaching BarChartNode.",
        "output_consumption": "'rendered' signal fires after the chart event is emitted. The chart data is delivered via on_display_data callback to the UI layer.",
        "common_combinations": [
            "OverseasStockAccountNode → BarChartNode (P&L per position)",
            "BenchmarkCompareNode → BarChartNode (performance metric comparison)",
            "ConditionNode → BarChartNode (current indicator snapshot per symbol)",
        ],
        "pitfalls": [
            "x_field and y_field must exactly match column names in the data — a typo produces an empty chart without an error message.",
            "If the data list has more than 20-30 items, bar labels on the x-axis become cramped. Consider limiting or aggregating upstream.",
            "BarChartNode does not sort bars automatically — sort the data before binding if you need ascending/descending order.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=BAR_CHART_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "array",
        "description": "i18n:display_schema.bar.description",
        "items": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "dynamic",
                    "resolved_by": "x_field",
                    "description": "i18n:display_schema.line.x",
                    "example": "category",
                },
                "y": {
                    "type": "dynamic",
                    "resolved_by": "y_field",
                    "description": "i18n:display_schema.line.y",
                    "example": "value",
                },
            },
            "required": ["x", "y"],
        },
    }

    x_field: Optional[str] = Field(
        default=None,
        description="X축 필드명",
    )

    y_field: Optional[str] = Field(
        default=None,
        description="Y축 필드명",
    )

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        schema = cls._common_field_schema()
        schema.update({
            "x_field": FieldSchema(
                name="x_field",
                type=FieldType.STRING,
                description="X축 필드명",
                placeholder="category",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
            "y_field": FieldSchema(
                name="y_field",
                type=FieldType.STRING,
                description="Y축 필드명",
                placeholder="value",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                required=True,
                group="field_mapping",
            ),
        })
        return schema


class SummaryDisplayNode(BaseDisplayNode):
    """JSON/요약 데이터 표시"""

    type: Literal["SummaryDisplayNode"] = "SummaryDisplayNode"
    description: str = "i18n:nodes.SummaryDisplayNode.description"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Display a single dict or JSON object as a formatted key-value summary (e.g. backtest metrics, AI agent response)",
            "Show raw API response or any arbitrary JSON for debugging or inspection",
            "Present the summary metrics output from BacktestEngineNode (total_return, sharpe, mdd) as a readable summary card",
        ],
        "when_not_to_use": [
            "For list[dict] data — use TableDisplayNode which renders rows properly",
            "For time-series visualization — use LineChartNode or CandlestickChartNode",
            "For category comparisons — use BarChartNode",
        ],
        "typical_scenarios": [
            "BacktestEngineNode → SummaryDisplayNode (summary port: total_return, sharpe, mdd as key-value display)",
            "AIAgentNode (text output) → SummaryDisplayNode (show the AI response text)",
            "HTTPRequestNode → SummaryDisplayNode (inspect raw API response for debugging)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Accepts any data type (dict, list, string, number) and renders it as formatted JSON or plain text",
        "Lightweight — no field configuration needed beyond 'data' binding and optional 'title'",
        "Emits on_display_data for real-time rendering in the workflow UI summary panel",
        "Ideal for single-object metrics dashboards where key-value display is preferred over a table grid",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using SummaryDisplayNode to display a list of 50+ rows of trade data",
            "reason": "SummaryDisplayNode renders the entire data as a JSON blob. Large lists are unreadable in summary format.",
            "alternative": "Use TableDisplayNode with appropriate column selection and row limit for list data.",
        },
        {
            "pattern": "Chaining SummaryDisplayNode output ('rendered' signal) to trigger business logic",
            "reason": "The 'rendered' signal only confirms the display event was emitted, not that the user has reviewed the data. It should not gate trading decisions.",
            "alternative": "Use ConditionNode or IfNode for conditional logic. SummaryDisplayNode is for visualization only.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Display backtest performance summary metrics",
            "description": "BacktestEngineNode outputs a 'summary' dict with total_return, sharpe, max_drawdown. SummaryDisplayNode renders it as a metrics card.",
            "workflow_snippet": {
                "id": "summary_backtest_metrics",
                "name": "Backtest Summary Display",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {"id": "backtest", "type": "BacktestEngineNode", "initial_capital": 10000, "commission_rate": 0.001, "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "AAPL", "exchange": "NASDAQ", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}}},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "RSI Backtest Results", "data": "{{ nodes.backtest.metrics }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "backtest"},
                    {"from": "backtest", "to": "summary"},
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
            "expected_output": "A summary card showing backtest metrics: total_return, sharpe_ratio, max_drawdown, win_rate.",
        },
        {
            "title": "Show AI agent text analysis result",
            "description": "AIAgentNode with output_format='text' produces a string response. SummaryDisplayNode presents it as a readable analysis card.",
            "workflow_snippet": {
                "id": "summary_ai_response",
                "name": "AI Analysis Summary",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o", "temperature": 0.3, "max_tokens": 500},
                    {"id": "agent", "type": "AIAgentNode", "system_prompt": "You are a concise financial analyst.", "user_prompt": "Summarize the current state of the US tech sector in 3 bullet points.", "output_format": "text", "max_tool_calls": 0, "cooldown_sec": 60},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "AI Market Analysis", "data": "{{ nodes.agent.response }}"},
                ],
                "edges": [
                    {"from": "start", "to": "llm"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "agent", "to": "summary"},
                ],
                "credentials": [
                    {
                        "credential_id": "llm_cred",
                        "type": "llm_openai",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "API Key"},
                        ],
                    }
                ],
            },
            "expected_output": "A summary card displaying the AI agent's 3-bullet market analysis as formatted text.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to any output — dict, string, number, or list. The node auto-formats the value as readable JSON or plain text depending on the data type. No additional field configuration is needed.",
        "output_consumption": "'rendered' signal fires after the display event is emitted. SummaryDisplayNode is typically the terminal node in a workflow branch — no further data consumption is expected.",
        "common_combinations": [
            "BacktestEngineNode.metrics → SummaryDisplayNode (performance summary card)",
            "AIAgentNode.response → SummaryDisplayNode (AI text or JSON output display)",
            "HTTPRequestNode.response → SummaryDisplayNode (raw API response inspection)",
        ],
        "pitfalls": [
            "SummaryDisplayNode renders list[dict] as a raw JSON array, not as a table — use TableDisplayNode for list data.",
            "Binding 'data' to a very large nested object (e.g. full historical time-series) produces a wall of JSON that is unreadable in the UI.",
            "The 'rendered' signal should not be used to gate trading decisions — it only signals that the display event was dispatched.",
        ],
    }

    _outputs: List[OutputPort] = [
        OutputPort(name="rendered", type="signal", description="i18n:ports.rendered", fields=SUMMARY_DISPLAY_FIELDS),
    ]

    _display_data_schema: ClassVar[Optional[Dict[str, Any]]] = {
        "type": "any",
        "description": "i18n:display_schema.summary.description",
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return cls._common_field_schema()

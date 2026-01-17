"""
ProgramGarden Core - Condition Nodes

Condition evaluation nodes:
- ConditionNode: Condition plugin execution (RSI, MACD, etc.)
- LogicNode: Condition combination (and/or/xor/at_least/weighted)
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class ConditionNode(PluginNode):
    """
    Condition plugin execution node

    Executes community plugins such as RSI, MACD, BollingerBands
    
    기본 입력 (필수):
    - data: OHLCV 배열 데이터 (플랫 형식)
    
    고급 옵션 (선택, 기본값 사용 가능):
    - close_field 등: 필드명 매핑 (커스텀 데이터 소스 사용 시)
    - symbols: 종목 리스트 (data에서 자동 추출됨)
    - held_symbols, position_data: 익절/손절 조건에서 사용
    
    예시:
    {
      "data": "{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
      "plugin": "RSI",
      "fields": {"period": 14, "threshold": 30}
    }
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.ConditionNode.description"

    # === 필수 입력 ===
    data: Any = Field(
        default=None,
        description="Input data array (e.g., {{ flatten(nodes.historicaldata_1.values, 'time_series') }})",
    )
    
    # === 고급: 필드 매핑 (기본값으로 충분, 커스텀 데이터 소스 사용 시만 변경) ===
    close_field: str = Field(
        default="close",
        description="Field name for close price",
    )
    open_field: str = Field(
        default="open",
        description="Field name for open price",
    )
    high_field: str = Field(
        default="high",
        description="Field name for high price",
    )
    low_field: str = Field(
        default="low",
        description="Field name for low price",
    )
    volume_field: str = Field(
        default="volume",
        description="Field name for volume",
    )
    date_field: str = Field(
        default="date",
        description="Field name for date/time",
    )
    symbol_field: str = Field(
        default="symbol",
        description="Field name for symbol identifier",
    )
    exchange_field: str = Field(
        default="exchange",
        description="Field name for exchange",
    )
    
    # === 익절/손절 플러그인 전용 입력 ===
    positions: Any = Field(
        default=None,
        description="Positions data binding - 익절/손절 플러그인용 (pnl_rate 포함)",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="data",
            type="array",
            description="i18n:ports.data",
        ),
        InputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.input_symbols",
        ),
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
        OutputPort(
            name="failed_symbols",
            type="symbol_list",
            description="i18n:ports.failed_symbols",
        ),
        OutputPort(
            name="values",
            type="dict",
            description="i18n:ports.values",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 플러그인 선택 ===
            "plugin": FieldSchema(
                name="plugin",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.plugin",
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="plugin_selector",
            ),
            # === DATA: 입력 데이터 ===
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.data",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
                example=[
                    {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260116", "close": 150.0, "open": 148.5, "high": 151.0, "low": 147.8, "volume": 1000000},
                ],
                example_binding="{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
                bindable_sources=[
                    "HistoricalDataNode.values (with flatten)",
                    "RealMarketDataNode.data",
                    "HTTPRequestNode.response",
                ],
                expected_type="list[dict]",
            ),
            # === FIELD MAPPING: 필드명 매핑 (data 바로 하단에 표시) ===
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.close_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="close",
                placeholder="close",
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.open_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="open",
                placeholder="open",
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.high_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="high",
                placeholder="high",
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.low_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="low",
                placeholder="low",
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.volume_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="volume",
                placeholder="volume",
                group="field_mapping",
            ),
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.date_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="date",
                placeholder="date",
                group="field_mapping",
            ),
            # === PLUGIN-SPECIFIC: 익절/손절 플러그인에서만 표시 ===
            # positions: v3.0.0+ 플러그인용 (ProfitTarget, StopLoss)
            "positions": FieldSchema(
                name="positions",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.positions",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realAccount.positions }}",
                example={"AAPL": {"qty": 10, "avg_price": 150.0, "pnl_rate": 5.5}},
                example_binding="{{ nodes.realAccount.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="dict[str, any]",
                visible_when={"plugin": ["ProfitTarget", "StopLoss", "TrailingStop"]},
                help_text="보유 포지션 데이터 (수익률 포함)",
            ),
            "symbol_field": FieldSchema(
                name="symbol_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.symbol_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="symbol",
                placeholder="symbol",
                group="field_mapping",
            ),
            "exchange_field": FieldSchema(
                name="exchange_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.exchange_field",
                required=False,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                default="exchange",
                placeholder="exchange",
                group="field_mapping",
            ),
        }


class LogicNode(BaseNode):
    """
    Condition combination node

    Combines multiple condition results with logical operators
    """

    type: Literal["LogicNode"] = "LogicNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.LogicNode.description"

    # LogicNode specific config
    operator: Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"] = Field(
        default="all",
        description="Logical operator (all=AND, any=OR, not, xor, at_least, at_most, exactly, weighted)",
    )
    threshold: Optional[int] = Field(
        default=None,
        description="Threshold value (for at_least, at_most, exactly operators)",
    )
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights (for weighted operator, weight per input ID)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input",
            type="condition_result",
            description="i18n:ports.result",
            multiple=True,
            min_connections=2,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 모두 핵심 논리 연산 설정 ===
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.LogicNode.operator",
                default="all",
                enum_values=["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"],
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "threshold": FieldSchema(
                name="threshold",
                type=FieldType.INTEGER,
                description="i18n:fields.LogicNode.threshold",
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
            ),
            "weights": FieldSchema(
                name="weights",
                type=FieldType.OBJECT,
                description="i18n:fields.LogicNode.weights",
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
        }


class PerformanceConditionNode(BaseNode):
    """
    Performance-based condition node

    Evaluates performance metrics (P&L, MDD, win rate, Sharpe ratio, etc.)
    from account or backtest data
    """

    type: Literal["PerformanceConditionNode"] = "PerformanceConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.PerformanceConditionNode.description"

    # === 포트 바인딩 필드 ===
    position_data: Any = Field(
        default=None,
        description="Position data binding (e.g., {{ nodes.account.positions }})",
    )
    balance_data: Any = Field(
        default=None,
        description="Balance data binding (e.g., {{ nodes.account.balance }})",
    )
    equity_curve: Any = Field(
        default=None,
        description="Equity curve data binding (e.g., {{ nodes.backtest.equity_curve }})",
    )
    trade_history: Any = Field(
        default=None,
        description="Trade history binding (e.g., {{ nodes.account.trade_history }})",
    )

    # === 성과 조건 설정 ===
    metric: Literal[
        "pnl_rate",           # 수익률 (%)
        "pnl_amount",         # 손익 금액
        "mdd",                # 최대 낙폭 (%)
        "win_rate",           # 승률 (%)
        "sharpe_ratio",       # 샤프 비율
        "profit_factor",      # 수익 팩터
        "avg_win",            # 평균 수익
        "avg_loss",           # 평균 손실
        "consecutive_wins",   # 연속 수익 횟수
        "consecutive_losses", # 연속 손실 횟수
        "total_trades",       # 총 거래 횟수
        "daily_pnl",          # 일일 손익
    ] = Field(
        default="pnl_rate",
        description="Performance metric to evaluate",
    )

    operator: Literal["gt", "lt", "gte", "lte", "eq", "ne"] = Field(
        default="gt",
        description="Comparison operator (gt=>, lt=<, gte=>=, lte=<=, eq===, ne=!=)",
    )

    threshold: float = Field(
        default=0.0,
        description="Threshold value to compare against",
    )

    # === 선택적 필터 ===
    symbol_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter specific symbols (None = all symbols)",
    )
    time_period: Optional[str] = Field(
        default=None,
        description="Time period for calculation (e.g., '1d', '1w', '1m', 'ytd', 'all')",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="position_data",
            type="position_data",
            description="i18n:ports.positions",
            required=False,
        ),
        InputPort(
            name="balance_data",
            type="balance_data",
            description="i18n:ports.balance",
            required=False,
        ),
        InputPort(
            name="equity_curve",
            type="equity_curve",
            description="i18n:ports.equity_curve",
            required=False,
        ),
        InputPort(
            name="trade_history",
            type="trade_list",
            description="i18n:ports.trade_history",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed",
            type="bool",
            description="i18n:ports.passed",
        ),
        OutputPort(
            name="metric_value",
            type="float",
            description="i18n:ports.metric_value",
        ),
        OutputPort(
            name="details",
            type="dict",
            description="i18n:ports.details",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 포트 바인딩 필드 ===
            "position_data": FieldSchema(
                name="position_data",
                type=FieldType.STRING,
                description="i18n:fields.PerformanceConditionNode.position_data",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.positions }}",
                example={"AAPL": {"qty": 10, "avg_price": 150.0, "pnl_rate": 5.2}},
                example_binding="{{ nodes.account.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="dict[str, any]",
            ),
            "balance_data": FieldSchema(
                name="balance_data",
                type=FieldType.STRING,
                description="i18n:fields.PerformanceConditionNode.balance_data",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.balance }}",
                example={"total": 100000, "available": 50000},
                example_binding="{{ nodes.account.balance }}",
                bindable_sources=[
                    "RealAccountNode.balance",
                    "AccountNode.balance",
                ],
                expected_type="dict[str, float]",
            ),
            "equity_curve": FieldSchema(
                name="equity_curve",
                type=FieldType.STRING,
                description="i18n:fields.PerformanceConditionNode.equity_curve",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.backtest.equity_curve }}",
                example=[{"date": "2024-01-01", "equity": 10000}, {"date": "2024-01-02", "equity": 10250}],
                example_binding="{{ nodes.backtest.equity_curve }}",
                bindable_sources=[
                    "BacktestEngineNode.equity_curve",
                ],
                expected_type="list[dict]",
            ),
            "trade_history": FieldSchema(
                name="trade_history",
                type=FieldType.STRING,
                description="i18n:fields.PerformanceConditionNode.trade_history",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.trade_history }}",
                example=[{"symbol": "AAPL", "pnl": 500}, {"symbol": "TSLA", "pnl": -200}],
                example_binding="{{ nodes.account.trade_history }}",
                bindable_sources=[
                    "AccountNode.trade_history",
                ],
                expected_type="list[dict]",
            ),
            # === PARAMETERS: 성과 조건 설정 ===
            "metric": FieldSchema(
                name="metric",
                type=FieldType.ENUM,
                description="i18n:fields.PerformanceConditionNode.metric",
                default="pnl_rate",
                enum_values=[
                    "pnl_rate", "pnl_amount", "mdd", "win_rate", "sharpe_ratio",
                    "profit_factor", "avg_win", "avg_loss", "consecutive_wins",
                    "consecutive_losses", "total_trades", "daily_pnl"
                ],
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.PerformanceConditionNode.operator",
                default="gt",
                enum_values=["gt", "lt", "gte", "lte", "eq", "ne"],
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "threshold": FieldSchema(
                name="threshold",
                type=FieldType.NUMBER,
                description="i18n:fields.PerformanceConditionNode.threshold",
                default=0.0,
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
            ),
            # === ADVANCED: 선택적 필터 ===
            "symbol_filter": FieldSchema(
                name="symbol_filter",
                type=FieldType.ARRAY,
                description="i18n:fields.PerformanceConditionNode.symbol_filter",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.SETTINGS,
            ),
            "time_period": FieldSchema(
                name="time_period",
                type=FieldType.ENUM,
                description="i18n:fields.PerformanceConditionNode.time_period",
                enum_values=["1d", "1w", "1m", "3m", "ytd", "all"],
                required=False,
                bindable=False,
                category=FieldCategory.SETTINGS,
            ),
        }

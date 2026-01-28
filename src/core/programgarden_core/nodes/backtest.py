"""
ProgramGarden Core - Backtest Nodes

Backtest execution and result analysis nodes:
- BacktestEngineNode: Unified backtest engine (execution + result)
- BenchmarkCompareNode: Benchmark comparison

HistoricalDataNode는 상품별 분리됨:
- backtest_stock.py → OverseasStockHistoricalDataNode
- backtest_futures.py → OverseasFuturesHistoricalDataNode
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
    EQUITY_CURVE_FIELDS,
    PERFORMANCE_METRICS_FIELDS,
    TRADE_FIELDS,
)


class BacktestEngineNode(BaseNode):
    """
    Unified backtest engine node

    Executes backtest with signals and historical data,
    then calculates performance metrics (return, MDD, Sharpe ratio, etc.)
    """

    type: Literal["BacktestEngineNode"] = "BacktestEngineNode"
    category: NodeCategory = NodeCategory.ANALYSIS
    description: str = "i18n:nodes.BacktestEngineNode.description"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Input data binding (required for UI rendering)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    data: Any = Field(
        default=None,
        description="OHLCV data for backtest (e.g., {{ flatten(nodes.historical.values, 'time_series') }})",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Field mapping (for custom data sources)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
    signal_field: str = Field(
        default="signal",
        description="Field name for trading signal (buy/sell)",
    )
    side_field: str = Field(
        default="side",
        description="Field name for position side (long/short, for futures)",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Basic backtest config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    initial_capital: float = Field(
        default=10000,
        description="i18n:fields.BacktestEngineNode.initial_capital",
    )
    commission_rate: float = Field(
        default=0.001,
        description="i18n:fields.BacktestEngineNode.commission_rate",
    )
    slippage: float = Field(
        default=0.0005,
        description="i18n:fields.BacktestEngineNode.slippage",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Position sizing config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    position_sizing: Literal["equal_weight", "kelly", "fixed_percent", "fixed_amount", "atr_based"] = Field(
        default="equal_weight",
        description="i18n:fields.BacktestEngineNode.position_sizing",
    )
    # Position sizing 개별 필드 (position_sizing 값에 따라 UI에서 동적 표시)
    kelly_fraction: Optional[float] = Field(
        default=0.25,
        description="i18n:fields.BacktestEngineNode.kelly_fraction",
    )
    max_position_percent: Optional[float] = Field(
        default=10.0,
        description="i18n:fields.BacktestEngineNode.max_position_percent",
    )
    fixed_percent: Optional[float] = Field(
        default=5.0,
        description="i18n:fields.BacktestEngineNode.fixed_percent",
    )
    fixed_amount: Optional[float] = Field(
        default=1000.0,
        description="i18n:fields.BacktestEngineNode.fixed_amount",
    )
    atr_risk_percent: Optional[float] = Field(
        default=1.0,
        description="i18n:fields.BacktestEngineNode.atr_risk_percent",
    )
    atr_period: Optional[int] = Field(
        default=14,
        description="i18n:fields.BacktestEngineNode.atr_period",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Exit rules config (개별 필드)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    stop_loss_percent: Optional[float] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.stop_loss_percent",
    )
    take_profit_percent: Optional[float] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.take_profit_percent",
    )
    trailing_stop_percent: Optional[float] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.trailing_stop_percent",
    )
    max_holding_days: Optional[int] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.max_holding_days",
    )
    time_stop_days: Optional[int] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.time_stop_days",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Result analysis config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # benchmark 필드 제거됨 - BenchmarkCompareNode 사용
    risk_free_rate: float = Field(
        default=0.02,
        description="i18n:fields.BacktestEngineNode.risk_free_rate",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Trading rules config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    allow_short: bool = Field(
        default=False,
        description="i18n:fields.BacktestEngineNode.allow_short",
    )
    allow_fractional: bool = Field(
        default=True,
        description="i18n:fields.BacktestEngineNode.allow_fractional",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Display config (for UI/reporting)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    strategy_name: Optional[str] = Field(
        default=None,
        description="i18n:fields.BacktestEngineNode.strategy_name",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="array",
            description="i18n:ports.data",
        ),
        InputPort(
            name="signals",
            type="signal_list",
            description="i18n:ports.signals",
        ),
        # PortfolioNode에서 자본 배분 받을 때 사용
        InputPort(
            name="allocated_capital",
            type="float",
            description="i18n:ports.allocated_capital",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="equity_curve",
            type="portfolio_result",
            description="i18n:ports.equity_curve",
            fields=EQUITY_CURVE_FIELDS,
        ),
        OutputPort(
            name="trades",
            type="trade_list",
            description="i18n:ports.trades",
            fields=TRADE_FIELDS,
        ),
        OutputPort(
            name="metrics",
            type="performance_summary",
            description="i18n:ports.metrics",
            fields=PERFORMANCE_METRICS_FIELDS,
        ),
        OutputPort(
            name="summary",
            type="performance_summary",
            description="i18n:ports.summary",
            fields=PERFORMANCE_METRICS_FIELDS,
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent
        )
        return {
            # === DATA: 입력 데이터 바인딩 ===
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.data",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                example=[
                    {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260116", "close": 150.0, "open": 148.5, "high": 151.0, "low": 147.8, "volume": 1000000},
                ],
                example_binding="{{ flatten(nodes.historical.values, 'time_series') }}",
                bindable_sources=["HistoricalDataNode.values", "ConditionNode.values"],
            ),
            # === FIELD MAPPING: 필드명 매핑 (기본값 사용 가능) ===
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.close_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="close",
                placeholder="close",
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.open_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="open",
                placeholder="open",
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.high_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="high",
                placeholder="high",
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.low_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="low",
                placeholder="low",
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.volume_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="volume",
                placeholder="volume",
                group="field_mapping",
            ),
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.date_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="date",
                placeholder="date",
                group="field_mapping",
            ),
            "symbol_field": FieldSchema(
                name="symbol_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.symbol_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="symbol",
                placeholder="symbol",
                group="field_mapping",
            ),
            "signal_field": FieldSchema(
                name="signal_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.signal_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="signal",
                placeholder="signal",
                group="field_mapping",
            ),
            "side_field": FieldSchema(
                name="side_field",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.side_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="side",
                placeholder="side",
                group="field_mapping",
            ),
            # === PARAMETERS: 핵심 백테스트 설정 ===
            "initial_capital": FieldSchema(
                name="initial_capital",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.initial_capital",
                default=10000,
                min_value=100,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=10000,
                example_binding="{{ nodes.portfolio.allocated_capital.strategy_1 }}",
                bindable_sources=["PortfolioNode.allocated_capital"],
                expected_type="float",
            ),
            "position_sizing": FieldSchema(
                name="position_sizing",
                type=FieldType.ENUM,
                description="i18n:fields.BacktestEngineNode.position_sizing",
                default="equal_weight",
                enum_values=["equal_weight", "kelly", "fixed_percent", "fixed_amount", "atr_based"],
                enum_labels={
                    "equal_weight": "i18n:enums.position_sizing.equal_weight",
                    "kelly": "i18n:enums.position_sizing.kelly",
                    "fixed_percent": "i18n:enums.position_sizing.fixed_percent",
                    "fixed_amount": "i18n:enums.position_sizing.fixed_amount",
                    "atr_based": "i18n:enums.position_sizing.atr_based",
                },
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="equal_weight",
                expected_type="str",
            ),
            # === Position Sizing 개별 필드 (depends_on으로 동적 표시) ===
            "kelly_fraction": FieldSchema(
                name="kelly_fraction",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.kelly_fraction",
                default=0.25,
                min_value=0.1,
                max_value=1.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["kelly"]},
                example=0.25,
                expected_type="float",
            ),
            "max_position_percent": FieldSchema(
                name="max_position_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.max_position_percent",
                default=10.0,
                min_value=1.0,
                max_value=100.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["kelly", "fixed_percent", "atr_based"]},
                example=10.0,
                expected_type="float",
            ),
            "fixed_percent": FieldSchema(
                name="fixed_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.fixed_percent",
                default=5.0,
                min_value=0.1,
                max_value=100.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["fixed_percent"]},
                example=5.0,
                expected_type="float",
            ),
            "fixed_amount": FieldSchema(
                name="fixed_amount",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.fixed_amount",
                default=1000.0,
                min_value=1.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["fixed_amount"]},
                example=1000.0,
                expected_type="float",
            ),
            "atr_risk_percent": FieldSchema(
                name="atr_risk_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.atr_risk_percent",
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["atr_based"]},
                example=1.0,
                expected_type="float",
            ),
            "atr_period": FieldSchema(
                name="atr_period",
                type=FieldType.INTEGER,
                description="i18n:fields.BacktestEngineNode.atr_period",
                default=14,
                min_value=1,
                max_value=100,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                depends_on={"position_sizing": ["atr_based"]},
                example=14,
                expected_type="int",
            ),
            # === Exit Rules 개별 필드 (항상 표시, 선택 입력) ===
            "stop_loss_percent": FieldSchema(
                name="stop_loss_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.stop_loss_percent",
                default=None,
                min_value=0.1,
                max_value=50.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=5.0,
                expected_type="float",
            ),
            "take_profit_percent": FieldSchema(
                name="take_profit_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.take_profit_percent",
                default=None,
                min_value=0.1,
                max_value=100.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=15.0,
                expected_type="float",
            ),
            "trailing_stop_percent": FieldSchema(
                name="trailing_stop_percent",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.trailing_stop_percent",
                default=None,
                min_value=0.1,
                max_value=50.0,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=3.0,
                expected_type="float",
            ),
            "max_holding_days": FieldSchema(
                name="max_holding_days",
                type=FieldType.INTEGER,
                description="i18n:fields.BacktestEngineNode.max_holding_days",
                default=None,
                min_value=1,
                max_value=365,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=30,
                expected_type="int",
            ),
            "time_stop_days": FieldSchema(
                name="time_stop_days",
                type=FieldType.INTEGER,
                description="i18n:fields.BacktestEngineNode.time_stop_days",
                default=None,
                min_value=1,
                max_value=365,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=10,
                expected_type="int",
            ),
            # benchmark 필드 제거됨 - BenchmarkCompareNode 사용
            # === SETTINGS: 부가 설정 ===
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.commission_rate",
                default=0.001,
                min_value=0,
                max_value=0.1,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=0.001,
                expected_type="float",
            ),
            "slippage": FieldSchema(
                name="slippage",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.slippage",
                default=0.0005,
                min_value=0,
                max_value=0.1,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=0.0005,
                expected_type="float",
            ),
            "risk_free_rate": FieldSchema(
                name="risk_free_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.BacktestEngineNode.risk_free_rate",
                default=0.02,
                min_value=0,
                max_value=0.2,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=0.02,
                expected_type="float",
            ),
            "allow_short": FieldSchema(
                name="allow_short",
                type=FieldType.BOOLEAN,
                description="i18n:fields.BacktestEngineNode.allow_short",
                default=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "allow_fractional": FieldSchema(
                name="allow_fractional",
                type=FieldType.BOOLEAN,
                description="i18n:fields.BacktestEngineNode.allow_fractional",
                default=True,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
            ),
            "strategy_name": FieldSchema(
                name="strategy_name",
                type=FieldType.STRING,
                description="i18n:fields.BacktestEngineNode.strategy_name",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="RSI Mean Reversion",
                expected_type="str",
            ),
        }


class BenchmarkCompareNode(BaseNode):
    """
    Benchmark comparison node

    Compares multiple backtest results (equity curves) and calculates
    comparison metrics, rankings, and combined visualization data.
    """

    type: Literal["BenchmarkCompareNode"] = "BenchmarkCompareNode"
    category: NodeCategory = NodeCategory.ANALYSIS
    description: str = "i18n:nodes.BenchmarkCompareNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/benchmark-compare.svg"

    # Dynamic input: multiple equity_curve bindings
    strategies: List[Any] = Field(
        default_factory=list,
        description="List of equity_curve data from BacktestEngineNode or strategy results",
    )

    # Field mapping (for custom data sources)
    date_field: str = Field(
        default="date",
        description="Field name for date/time",
    )
    equity_field: str = Field(
        default="equity",
        description="Field name for equity/capital value",
    )
    name_field: str = Field(
        default="strategy_name",
        description="Field name for strategy name",
    )

    # Comparison settings
    ranking_metric: Literal["sharpe", "return", "mdd", "calmar"] = Field(
        default="sharpe",
        description="i18n:fields.BenchmarkCompareNode.ranking_metric",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="strategies",
            type="array",
            description="i18n:ports.strategies",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="combined_curve",
            type="array",
            description="i18n:ports.combined_curve",
            fields=EQUITY_CURVE_FIELDS,
        ),
        OutputPort(
            name="comparison_metrics",
            type="array",
            description="i18n:ports.comparison_metrics",
            fields=PERFORMANCE_METRICS_FIELDS,
        ),
        OutputPort(
            name="ranking",
            type="array",
            description="i18n:ports.ranking",
            fields=PERFORMANCE_METRICS_FIELDS,
        ),
        OutputPort(
            name="strategies_meta",
            type="array",
            description="i18n:ports.strategies_meta",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode
        )
        return {
            "strategies": FieldSchema(
                name="strategies",
                type=FieldType.ARRAY,
                description="i18n:fields.BenchmarkCompareNode.strategies",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                example=[
                    {"strategy_name": "RSI Strategy", "equity_curve": [{"date": "20260101", "equity": 10500}]},
                    {"strategy_name": "SPY Buy&Hold", "equity_curve": [{"date": "20260101", "equity": 10200}]},
                ],
                example_binding="[{{ nodes.backtest_rsi }}, {{ nodes.backtest_spy }}]",
                bindable_sources=[
                    "BacktestEngineNode.equity_curve",
                    "BacktestEngineNode",
                    "PortfolioNode.equity_curve",
                    "HTTPRequestNode.response",
                ],
                expected_type="list[dict | equity_curve]",
            ),
            # === FIELD MAPPING: 필드명 매핑 (기본값 사용 가능) ===
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="i18n:fields.BenchmarkCompareNode.date_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="date",
                placeholder="date",
                group="field_mapping",
                collapsed=True,
            ),
            "equity_field": FieldSchema(
                name="equity_field",
                type=FieldType.STRING,
                description="i18n:fields.BenchmarkCompareNode.equity_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="equity",
                placeholder="equity",
                group="field_mapping",
                collapsed=True,
            ),
            "name_field": FieldSchema(
                name="name_field",
                type=FieldType.STRING,
                description="i18n:fields.BenchmarkCompareNode.name_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="strategy_name",
                placeholder="strategy_name",
                group="field_mapping",
                collapsed=True,
            ),
            # === PARAMETERS: 비교 설정 ===
            "ranking_metric": FieldSchema(
                name="ranking_metric",
                type=FieldType.ENUM,
                description="i18n:fields.BenchmarkCompareNode.ranking_metric",
                default="sharpe",
                enum_values=["sharpe", "return", "mdd", "calmar"],
                enum_labels={
                    "sharpe": "i18n:enums.ranking_metric.sharpe",
                    "return": "i18n:enums.ranking_metric.return",
                    "mdd": "i18n:enums.ranking_metric.mdd",
                    "calmar": "i18n:enums.ranking_metric.calmar",
                },
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="sharpe",
                expected_type="str",
            ),
        }
"""
ProgramGarden Core - Backtest Nodes

Backtest execution and result analysis nodes:
- BacktestEngineNode: Unified backtest engine (execution + result)
- HistoricalDataNode: Historical data query
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


class HistoricalDataNode(BaseNode):
    """
    Historical data query node

    Fetches historical OHLCV data for backtesting
    """

    type: Literal["HistoricalDataNode"] = "HistoricalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.HistoricalDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/historicaldata.svg"

    # HistoricalDataNode specific config
    start_date: str = Field(
        default="dynamic:months_ago(3)",
        description="Start date (YYYY-MM-DD or dynamic:months_ago(N))",
    )
    end_date: str = Field(
        default="dynamic:today()",
        description="End date (YYYY-MM-DD or dynamic:today())",
    )
    interval: str = Field(
        default="1d",
        description="Data interval (1m, 5m, 15m, 1h, 1d)",
    )
    adjust: bool = Field(
        default=True,
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
        OutputPort(
            name="ohlcv_data",
            type="ohlcv_data",
            description="i18n:ports.ohlcv_data",
        ),
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 데이터 조회 설정 ===
            "start_date": FieldSchema(
                name="start_date",
                type=FieldType.STRING,
                description="i18n:fields.HistoricalDataNode.start_date",
                default="dynamic:months_ago(3)",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="2024-01-01",
                expected_type="str",
            ),
            "end_date": FieldSchema(
                name="end_date",
                type=FieldType.STRING,
                description="i18n:fields.HistoricalDataNode.end_date",
                default="dynamic:today()",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="2024-12-31",
                expected_type="str",
            ),
            "interval": FieldSchema(
                name="interval",
                type=FieldType.STRING,
                description="i18n:fields.HistoricalDataNode.interval",
                default="1d",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="1d",
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "adjust": FieldSchema(
                name="adjust",
                type=FieldType.BOOLEAN,
                description="i18n:fields.HistoricalDataNode.adjust",
                default=True,
                category=FieldCategory.SETTINGS,
                bindable=False,
            ),
        }


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
    # Basic backtest config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    initial_capital: float = Field(
        default=10000,
        description="Initial capital (can be overridden by parent PortfolioNode)",
    )
    commission_rate: float = Field(
        default=0.001,
        description="Commission rate (0.001 = 0.1%)",
    )
    slippage: float = Field(
        default=0.0005,
        description="Slippage (0.0005 = 0.05%)",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Position sizing config (extended)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    position_sizing: Literal["equal_weight", "kelly", "fixed_percent", "fixed_amount", "atr_based"] = Field(
        default="equal_weight",
        description="Position sizing method",
    )
    position_sizing_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Position sizing detailed config (method-specific parameters)",
    )
    # position_sizing_config 예시:
    # {
    #     "max_position_percent": 10.0,   # 종목당 최대 비중 (%)
    #     "kelly_fraction": 0.25,         # Kelly 비율 (0.25 = 1/4 Kelly)
    #     "fixed_amount": 1000,           # 고정 금액 (fixed_amount 방식)
    #     "fixed_percent": 5.0,           # 고정 비율 (%) (fixed_percent 방식)
    #     "atr_risk_percent": 1.0,        # ATR 리스크 % (atr_based 방식)
    #     "atr_period": 14,               # ATR 계산 기간
    # }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Exit rules config (extended)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    exit_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Exit rules for automatic position closing",
    )
    # exit_rules 예시:
    # {
    #     "stop_loss_percent": 5.0,       # 손절 % (매수가 대비)
    #     "take_profit_percent": 15.0,    # 익절 % (매수가 대비)
    #     "trailing_stop_percent": 3.0,   # 트레일링 스탑 % (고점 대비)
    #     "max_holding_days": 30,         # 최대 보유 기간 (일)
    #     "time_stop_days": 10,           # 시간 손절 (N일 후 수익 없으면 청산)
    # }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Result analysis config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    benchmark: Optional[str] = Field(
        default=None,
        description="Benchmark symbol (e.g., SPY)",
    )
    risk_free_rate: float = Field(
        default=0.02,
        description="Risk-free rate (for Sharpe ratio calculation)",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Trading rules config
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    allow_short: bool = Field(
        default=False,
        description="Allow short selling",
    )
    allow_fractional: bool = Field(
        default=True,
        description="Allow fractional shares",
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Display config (for UI/reporting)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    strategy_name: Optional[str] = Field(
        default=None,
        description="Strategy name (for display purposes)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="ohlcv_data",
            type="ohlcv_data",
            description="i18n:ports.ohlcv_data",
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
        ),
        OutputPort(
            name="trades",
            type="trade_list",
            description="i18n:ports.trades",
        ),
        OutputPort(
            name="metrics",
            type="performance_summary",
            description="i18n:ports.metrics",
        ),
        OutputPort(
            name="summary",
            type="performance_summary",
            description="i18n:ports.summary",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 백테스트 설정 ===
            "initial_capital": FieldSchema(
                name="initial_capital",
                type=FieldType.NUMBER,
                description="Initial capital for backtest. Can be overridden by parent PortfolioNode allocation.",
                default=10000,
                min_value=100,
                category=FieldCategory.PARAMETERS,
                bindable=True,
                expression_enabled=True,
                example=10000,
                example_binding="{{ nodes.portfolio.allocated_capital.strategy_1 }}",
                bindable_sources=["PortfolioNode.allocated_capital"],
                expected_type="float",
            ),
            "position_sizing": FieldSchema(
                name="position_sizing",
                type=FieldType.ENUM,
                description="Position sizing method. equal_weight: divide equally. kelly: Kelly criterion. fixed_percent: fixed % of capital. fixed_amount: fixed dollar amount. atr_based: ATR volatility-based.",
                default="equal_weight",
                enum_values=["equal_weight", "kelly", "fixed_percent", "fixed_amount", "atr_based"],
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="equal_weight",
                expected_type="str",
            ),
            "position_sizing_config": FieldSchema(
                name="position_sizing_config",
                type=FieldType.OBJECT,
                description="Position sizing parameters. Options: max_position_percent, kelly_fraction, fixed_amount, fixed_percent, atr_risk_percent, atr_period.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"max_position_percent": 10.0, "kelly_fraction": 0.25},
                expected_type="dict[str, Any]",
            ),
            "exit_rules": FieldSchema(
                name="exit_rules",
                type=FieldType.OBJECT,
                description="Automatic exit rules. Options: stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_days, time_stop_days.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"stop_loss_percent": 5.0, "take_profit_percent": 15.0, "trailing_stop_percent": 3.0},
                expected_type="dict[str, Any]",
            ),
            "benchmark": FieldSchema(
                name="benchmark",
                type=FieldType.STRING,
                description="Benchmark symbol for comparison. Common options: SPY, QQQ, IWM.",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="SPY",
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "commission_rate": FieldSchema(
                name="commission_rate",
                type=FieldType.NUMBER,
                description="Commission rate as decimal. e.g., 0.001 = 0.1% per trade.",
                default=0.001,
                min_value=0,
                max_value=0.1,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=0.001,
                expected_type="float",
            ),
            "slippage": FieldSchema(
                name="slippage",
                type=FieldType.NUMBER,
                description="Slippage as decimal. e.g., 0.0005 = 0.05% price impact.",
                default=0.0005,
                min_value=0,
                max_value=0.1,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=0.0005,
                expected_type="float",
            ),
            "risk_free_rate": FieldSchema(
                name="risk_free_rate",
                type=FieldType.NUMBER,
                description="Annual risk-free rate for Sharpe ratio calculation. e.g., 0.02 = 2%.",
                default=0.02,
                min_value=0,
                max_value=0.2,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=0.02,
                expected_type="float",
            ),
            "allow_short": FieldSchema(
                name="allow_short",
                type=FieldType.BOOLEAN,
                description="Allow short selling. When true, negative signals create short positions.",
                default=False,
                category=FieldCategory.SETTINGS,
                bindable=False,
            ),
            "allow_fractional": FieldSchema(
                name="allow_fractional",
                type=FieldType.BOOLEAN,
                description="Allow fractional shares. When false, positions are rounded to whole shares.",
                default=True,
                category=FieldCategory.SETTINGS,
                bindable=False,
            ),
            "strategy_name": FieldSchema(
                name="strategy_name",
                type=FieldType.STRING,
                description="Strategy name for display in reports and charts.",
                required=False,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example="RSI Mean Reversion",
                expected_type="str",
            ),
        }


class PerformanceConditionNode(BaseNode):
    """
    Performance condition validation node

    Validates whether backtest results meet specified criteria
    """

    type: Literal["PerformanceConditionNode"] = "PerformanceConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.PerformanceConditionNode.description"

    # PerformanceConditionNode specific config
    conditions: dict = Field(
        default_factory=dict,
        description="Performance conditions (e.g., {'total_return': '>0', 'max_drawdown': '<10'})",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="performance_data",
            type="performance_summary",
            description="i18n:ports.performance_data",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="passed",
            type="signal",
            description="i18n:ports.passed",
        ),
        OutputPort(
            name="failed",
            type="signal",
            description="i18n:ports.failed",
        ),
        OutputPort(
            name="result",
            type="dict",
            description="i18n:ports.result",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 조건 설정 ===
            "conditions": FieldSchema(
                name="conditions",
                type=FieldType.OBJECT,
                description="Performance validation conditions. Use comparison operators: '>N', '<N', '>=N', '<=N'. Available metrics: total_return, max_drawdown, sharpe_ratio, win_rate.",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"total_return": ">0", "max_drawdown": "<10", "sharpe_ratio": ">1.0"},
                expected_type="dict[str, str]",
            ),
        }
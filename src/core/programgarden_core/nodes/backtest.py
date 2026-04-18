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
    # Input data binding: items { from, extract }
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    items: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data input configuration with from (source array) and extract (field mapping)",
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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Simulate a trading strategy on historical OHLCV data to evaluate performance before live deployment",
            "Calculate performance metrics (total return, Sharpe ratio, MDD, win rate) for a signal-based strategy",
            "Test different position sizing methods (equal weight, Kelly, fixed percent, ATR-based) against the same signal set",
            "Compare multiple stop-loss and take-profit combinations to find optimal exit parameters",
        ],
        "when_not_to_use": [
            "For live trading — BacktestEngineNode is for historical simulation only. Use NewOrderNode for live orders.",
            "When you only need to visualize raw historical prices without signal simulation — use HistoricalDataNode directly",
            "For real-time paper trading simulation — use actual broker nodes with paper_trading=True",
        ],
        "typical_scenarios": [
            "OverseasStockHistoricalDataNode → ConditionNode → BacktestEngineNode → LineChartNode (equity curve)",
            "OverseasStockHistoricalDataNode → ConditionNode → BacktestEngineNode → BenchmarkCompareNode → MultiLineChartNode",
            "PortfolioNode → BacktestEngineNode (allocated_capital port for multi-strategy capital allocation)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Unified engine: executes backtest AND computes performance metrics in a single node",
        "Five position sizing modes: equal_weight, kelly, fixed_percent, fixed_amount, atr_based",
        "Configurable exit rules: stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_days",
        "Outputs four ports: equity_curve (time series), trades (log), metrics (summary dict), summary (alias for metrics)",
        "Commission and slippage parameters for realistic cost modeling",
        "allow_short flag enables short-selling simulation; allow_fractional enables fractional share sizing",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using BacktestEngineNode without setting commission_rate and slippage",
            "reason": "With zero costs the backtest overfits to the historical data and shows unrealistically high returns that cannot be achieved live.",
            "alternative": "Always set commission_rate (e.g. 0.001 = 0.1%) and slippage (e.g. 0.0005) to model realistic trading costs.",
        },
        {
            "pattern": "Running BacktestEngineNode on only 30 days of data to validate a long-term strategy",
            "reason": "Short backtest periods are statistically unreliable. A strategy can appear profitable by chance on 30 days.",
            "alternative": "Use at least 1-2 years of daily data (252-504 bars) or equivalent intraday data for meaningful results.",
        },
        {
            "pattern": "Optimizing stop_loss_percent across dozens of backtests on the same dataset without out-of-sample testing",
            "reason": "Repeated optimization on the same data leads to curve-fitting. The optimal parameters will likely fail on new data.",
            "alternative": "Split data into in-sample (training) and out-of-sample (validation) periods. Only optimize on the training set.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "RSI mean-reversion backtest for AAPL",
            "description": "Fetch 1 year of daily AAPL data, generate RSI signals, run a backtest with equal-weight sizing and 5% stop-loss, then chart the equity curve.",
            "workflow_snippet": {
                "id": "backtest_rsi_aapl",
                "name": "RSI Backtest AAPL",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {
                        "id": "backtest",
                        "type": "BacktestEngineNode",
                        "initial_capital": 10000,
                        "commission_rate": 0.001,
                        "slippage": 0.0005,
                        "position_sizing": "equal_weight",
                        "stop_loss_percent": 5.0,
                        "risk_free_rate": 0.02,
                        "items": {
                            "from": "{{ nodes.historical.values }}",
                            "extract": {
                                "symbol": "AAPL",
                                "exchange": "NASDAQ",
                                "date": "{{ row.date }}",
                                "open": "{{ row.open }}",
                                "high": "{{ row.high }}",
                                "low": "{{ row.low }}",
                                "close": "{{ row.close }}",
                                "signal": "{{ row.signal }}",
                            },
                        },
                    },
                    {"id": "chart", "type": "LineChartNode", "title": "RSI Strategy Equity", "data": "{{ nodes.backtest.equity_curve }}", "x_field": "date", "y_field": "equity"},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "Performance Metrics", "data": "{{ nodes.backtest.metrics }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "backtest"},
                    {"from": "backtest", "to": "chart"},
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
            "expected_output": "equity_curve (list of {date, equity}), metrics: {total_return, sharpe_ratio, max_drawdown, win_rate, total_trades}.",
        },
        {
            "title": "MACD trend-following backtest with trailing stop",
            "description": "Use MACD signals on SPY with a 3% trailing stop and Kelly position sizing to simulate a trend-following strategy.",
            "workflow_snippet": {
                "id": "backtest_macd_spy",
                "name": "MACD Trailing Stop Backtest",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}], "period": "1d", "count": 504},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {
                        "id": "backtest",
                        "type": "BacktestEngineNode",
                        "initial_capital": 50000,
                        "commission_rate": 0.001,
                        "slippage": 0.0005,
                        "position_sizing": "kelly",
                        "kelly_fraction": 0.25,
                        "trailing_stop_percent": 3.0,
                        "risk_free_rate": 0.04,
                        "items": {
                            "from": "{{ nodes.historical.values }}",
                            "extract": {
                                "symbol": "SPY",
                                "exchange": "NYSE",
                                "date": "{{ row.date }}",
                                "open": "{{ row.open }}",
                                "high": "{{ row.high }}",
                                "low": "{{ row.low }}",
                                "close": "{{ row.close }}",
                                "signal": "{{ row.signal }}",
                            },
                        },
                    },
                    {"id": "chart", "type": "LineChartNode", "title": "MACD Kelly Equity Curve", "data": "{{ nodes.backtest.equity_curve }}", "x_field": "date", "y_field": "equity"},
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
            "expected_output": "equity_curve with trailing-stop exits visible as sharp drops halted at 3% below the peak, plus metrics showing Kelly-adjusted returns.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "The 'items' field uses a {from, extract} structure. 'from' is an expression pointing to the historical data array. 'extract' maps column names (symbol, exchange, date, open, high, low, close, signal) from each row using {{ row.fieldName }} expressions. The 'signal' extract field must match the column name that ConditionNode writes buy/sell signals to.",
        "output_consumption": "Use 'equity_curve' for time-series visualization (LineChartNode, MultiLineChartNode). Use 'trades' for a detailed trade-by-trade table (TableDisplayNode). Use 'metrics' or 'summary' (identical) for the performance summary card (SummaryDisplayNode). Feed 'equity_curve' into BenchmarkCompareNode for multi-strategy comparison.",
        "common_combinations": [
            "HistoricalDataNode → ConditionNode → BacktestEngineNode → LineChartNode (equity curve)",
            "BacktestEngineNode.trades → TableDisplayNode (trade log)",
            "BacktestEngineNode.metrics → SummaryDisplayNode (performance metrics card)",
            "BacktestEngineNode.equity_curve → BenchmarkCompareNode → MultiLineChartNode",
        ],
        "pitfalls": [
            "The 'extract.signal' value must exactly match the signal field name in ConditionNode output — a mismatch results in zero signals and the backtest runs as buy-and-hold.",
            "initial_capital must be at least 100. Setting it too low causes position sizing to fail with zero-quantity orders.",
            "BacktestEngineNode runs synchronously — very large datasets (10,000+ rows, 50+ symbols) can make the workflow cycle slow. Consider reducing count or using daily rather than intraday data.",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(
            name="items",
            type="array",
            description="i18n:ports.items",
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
            # === DATA: items { from, extract } 방식 ===
            "items": FieldSchema(
                name="items",
                type=FieldType.OBJECT,
                description="i18n:fields.BacktestEngineNode.items",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                help_text="i18n:fields.BacktestEngineNode.items.help_text",
                object_schema=[
                    {
                        "name": "from",
                        "type": "STRING",
                        "expression_mode": "expression_only",
                        "required": True,
                        "description": "i18n:fields.BacktestEngineNode.items.from",
                        "placeholder": "{{ nodes.historical.value.time_series }}",
                        "help_text": "반복할 배열을 지정합니다. 이 배열의 각 항목을 row로 접근할 수 있습니다.",
                    },
                    {
                        "name": "extract",
                        "type": "OBJECT",
                        "expression_mode": "fixed_only",
                        "required": True,
                        "description": "i18n:fields.BacktestEngineNode.items.extract",
                        "help_text": "각 행에서 추출할 필드를 정의합니다. row.xxx로 현재 행의 필드에 접근합니다.",
                        "object_schema": [
                            {"name": "symbol", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "종목 코드", "placeholder": "{{ nodes.split.item.symbol }}"},
                            {"name": "exchange", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "거래소 코드", "placeholder": "{{ nodes.split.item.exchange }}"},
                            {"name": "date", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "날짜", "placeholder": "{{ row.date }}"},
                            {"name": "open", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "시가", "placeholder": "{{ row.open }}"},
                            {"name": "high", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "고가", "placeholder": "{{ row.high }}"},
                            {"name": "low", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "저가", "placeholder": "{{ row.low }}"},
                            {"name": "close", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "종가", "placeholder": "{{ row.close }}"},
                            {"name": "volume", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "거래량", "placeholder": "{{ row.volume }}"},
                            {"name": "signal", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "매매 신호", "placeholder": "{{ nodes.condition.result.signal }}"},
                            {"name": "side", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "포지션 방향", "placeholder": "{{ nodes.condition.result.side }}"},
                        ],
                    },
                ],
                example={
                    "from": "{{ nodes.historical.value.time_series }}",
                    "extract": {
                        "symbol": "{{ nodes.split.item.symbol }}",
                        "exchange": "{{ nodes.split.item.exchange }}",
                        "date": "{{ row.date }}",
                        "open": "{{ row.open }}",
                        "high": "{{ row.high }}",
                        "low": "{{ row.low }}",
                        "close": "{{ row.close }}",
                        "volume": "{{ row.volume }}",
                        "signal": "{{ nodes.condition.result.signal }}",
                    },
                },
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
    _img_url: ClassVar[str] = ""

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compare two or more backtest equity curves side by side using a common performance metric (Sharpe, return, MDD, Calmar)",
            "Rank multiple strategies by a chosen metric to identify the best performer",
            "Generate a combined_curve for MultiLineChartNode to visualize all strategies on a single chart",
            "Produce a comparison_metrics table for TableDisplayNode or BarChartNode to compare returns across strategies",
        ],
        "when_not_to_use": [
            "For comparing a single strategy against itself — BenchmarkCompareNode needs at least two equity curves",
            "For live strategy ranking — this node operates on historical backtest outputs only",
            "For computing raw performance metrics of a single strategy — use BacktestEngineNode.metrics directly",
        ],
        "typical_scenarios": [
            "BacktestEngineNode (RSI) + BacktestEngineNode (MACD) → BenchmarkCompareNode → MultiLineChartNode",
            "BenchmarkCompareNode → BarChartNode (x=strategy_name, y=sharpe — Sharpe ratio bar chart)",
            "BenchmarkCompareNode → TableDisplayNode (ranking — sorted strategy leaderboard)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Accepts a list of equity_curve arrays from multiple BacktestEngineNode outputs for head-to-head comparison",
        "Outputs combined_curve (all series merged) for MultiLineChartNode visualization",
        "Outputs comparison_metrics and ranking (sorted by ranking_metric) for tabular display",
        "Configurable ranking_metric: sharpe (default), return, mdd, calmar",
        "date_field, equity_field, name_field can be customized for non-standard data sources",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Feeding raw price data (not equity curves) into BenchmarkCompareNode",
            "reason": "BenchmarkCompareNode expects equity curve format {date, equity, strategy_name}. Raw OHLCV price data has a different schema and will produce incorrect metrics.",
            "alternative": "Always use BacktestEngineNode.equity_curve as input. Run a buy-and-hold backtest for the benchmark asset (SPY) as the reference curve.",
        },
        {
            "pattern": "Comparing strategies backtested on different date ranges",
            "reason": "Strategies with different start/end dates are compared over misaligned time periods, making performance metrics incomparable.",
            "alternative": "Ensure all BacktestEngineNode instances use the same historical data date range before feeding into BenchmarkCompareNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Compare RSI strategy vs MACD strategy on SPY",
            "description": "Run two BacktestEngineNodes (RSI and MACD signals) on the same SPY history, then rank them by Sharpe ratio.",
            "workflow_snippet": {
                "id": "benchmark_rsi_vs_macd",
                "name": "RSI vs MACD Comparison",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}], "period": "1d", "count": 252},
                    {"id": "rsi_cond", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {"id": "macd_cond", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {
                        "id": "backtest_rsi",
                        "type": "BacktestEngineNode",
                        "initial_capital": 10000,
                        "commission_rate": 0.001,
                        "slippage": 0.0005,
                        "position_sizing": "equal_weight",
                        "strategy_name": "RSI Strategy",
                        "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "SPY", "exchange": "NYSE", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}},
                    },
                    {
                        "id": "backtest_macd",
                        "type": "BacktestEngineNode",
                        "initial_capital": 10000,
                        "commission_rate": 0.001,
                        "slippage": 0.0005,
                        "position_sizing": "equal_weight",
                        "strategy_name": "MACD Strategy",
                        "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "SPY", "exchange": "NYSE", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}},
                    },
                    {"id": "benchmark", "type": "BenchmarkCompareNode", "strategies": "{{ [nodes.backtest_rsi.equity_curve, nodes.backtest_macd.equity_curve] }}", "ranking_metric": "sharpe"},
                    {"id": "ranking_table", "type": "TableDisplayNode", "title": "Strategy Ranking", "data": "{{ nodes.benchmark.ranking }}", "limit": 10},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "rsi_cond"},
                    {"from": "historical", "to": "macd_cond"},
                    {"from": "rsi_cond", "to": "backtest_rsi"},
                    {"from": "macd_cond", "to": "backtest_macd"},
                    {"from": "backtest_rsi", "to": "benchmark"},
                    {"from": "backtest_macd", "to": "benchmark"},
                    {"from": "benchmark", "to": "ranking_table"},
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
            "expected_output": "ranking table listing RSI Strategy and MACD Strategy sorted by Sharpe ratio descending, with columns: strategy_name, total_return, sharpe, max_drawdown.",
        },
        {
            "title": "Multi-strategy equity curve comparison chart",
            "description": "Feed combined_curve from BenchmarkCompareNode to MultiLineChartNode to visualize all strategy equity curves on one chart.",
            "workflow_snippet": {
                "id": "benchmark_multiline",
                "name": "Multi-Strategy Equity Chart",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "QQQ", "exchange": "NASDAQ"}], "period": "1d", "count": 252},
                    {"id": "condition", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.historical.values }}"},
                    {
                        "id": "backtest",
                        "type": "BacktestEngineNode",
                        "initial_capital": 10000,
                        "commission_rate": 0.001,
                        "slippage": 0.0005,
                        "position_sizing": "equal_weight",
                        "strategy_name": "MACD QQQ",
                        "items": {"from": "{{ nodes.historical.values }}", "extract": {"symbol": "QQQ", "exchange": "NASDAQ", "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}", "low": "{{ row.low }}", "close": "{{ row.close }}", "signal": "{{ row.signal }}"}},
                    },
                    {"id": "benchmark", "type": "BenchmarkCompareNode", "strategies": "{{ nodes.backtest.equity_curve }}", "ranking_metric": "sharpe"},
                    {"id": "chart", "type": "MultiLineChartNode", "title": "Equity Curve Comparison", "data": "{{ nodes.benchmark.combined_curve }}", "x_field": "date", "y_field": "equity", "series_key": "strategy_name"},
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
            "expected_output": "A multi-line chart showing the equity curve for MACD QQQ strategy, with strategy_name as the series differentiator.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "The 'strategies' field expects a list of equity_curve arrays. Each equity_curve item must contain date, equity, and strategy_name fields (or customize via date_field, equity_field, name_field). Bind using an expression that wraps multiple BacktestEngineNode.equity_curve outputs into a list.",
        "output_consumption": "Use 'combined_curve' → MultiLineChartNode for visualization. Use 'comparison_metrics' → TableDisplayNode or BarChartNode for metric comparison. Use 'ranking' → TableDisplayNode for sorted leaderboard display.",
        "common_combinations": [
            "BacktestEngineNode (x2+) → BenchmarkCompareNode → MultiLineChartNode",
            "BenchmarkCompareNode.ranking → TableDisplayNode",
            "BenchmarkCompareNode.comparison_metrics → BarChartNode (Sharpe bar chart)",
        ],
        "pitfalls": [
            "All strategy equity curves must cover the same date range — misaligned dates cause incorrect comparison metrics.",
            "strategy_name must be unique per equity curve. If multiple BacktestEngineNodes have the same strategy_name, the ranking will have duplicate entries.",
            "BenchmarkCompareNode does not fetch benchmark data (SPY, QQQ) automatically. You must run a separate buy-and-hold BacktestEngineNode and include its equity_curve in the strategies list.",
        ],
    }

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
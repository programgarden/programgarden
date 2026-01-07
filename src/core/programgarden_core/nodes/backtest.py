"""
ProgramGarden Core - Backtest Nodes

Backtest execution and result analysis nodes:
- BacktestEngineNode: Unified backtest engine (execution + result)
- HistoricalDataNode: Historical data query
"""

from typing import Optional, List, Literal
from pydantic import Field

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
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.HistoricalDataNode.description"

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


class BacktestEngineNode(BaseNode):
    """
    Unified backtest engine node

    Executes backtest with signals and historical data,
    then calculates performance metrics (return, MDD, Sharpe ratio, etc.)
    """

    type: Literal["BacktestEngineNode"] = "BacktestEngineNode"
    category: NodeCategory = NodeCategory.BACKTEST
    description: str = "i18n:nodes.BacktestEngineNode.description"

    # Backtest execution config
    initial_capital: float = Field(
        default=10000,
        description="Initial capital",
    )
    commission_rate: float = Field(
        default=0.001,
        description="Commission rate (0.001 = 0.1%)",
    )
    slippage: float = Field(
        default=0.0005,
        description="Slippage (0.0005 = 0.05%)",
    )
    position_sizing: Literal["equal_weight", "kelly", "fixed"] = Field(
        default="equal_weight",
        description="Position sizing method",
    )
    
    # Result analysis config
    benchmark: Optional[str] = Field(
        default=None,
        description="Benchmark symbol (e.g., SPY)",
    )
    risk_free_rate: float = Field(
        default=0.02,
        description="Risk-free rate (for Sharpe ratio calculation)",
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
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="equity_curve",
            type="time_series",
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

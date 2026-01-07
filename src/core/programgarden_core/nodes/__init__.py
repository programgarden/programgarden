"""
ProgramGarden Core - 노드 타입 정의

37개 노드 타입을 15개 카테고리로 분류:
- infra (2): StartNode, BrokerNode
- realtime (3): RealMarketDataNode, RealAccountNode, RealOrderEventNode
- data (4): MarketDataNode, HistoricalDataNode, SQLiteNode, PostgresNode
- account (1): AccountNode
- symbol (4): WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode
- trigger (3): ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode
- condition (3): ConditionNode, LogicNode, PerformanceConditionNode
- risk (3): PositionSizingNode, RiskGuardNode, RiskConditionNode
- order (4): NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode
- event (3): EventHandlerNode, ErrorHandlerNode, AlertNode
- display (1): DisplayNode
- group (1): GroupNode
- backtest (1): BacktestEngineNode
- job (3): DeployNode, TradingHaltNode, JobControlNode
- calculation (1): PnLCalculatorNode
"""

from programgarden_core.nodes.base import BaseNode, NodeCategory, Position
from programgarden_core.nodes.infra import StartNode, BrokerNode
from programgarden_core.nodes.realtime import (
    RealMarketDataNode,
    RealAccountNode,
    RealOrderEventNode,
)
from programgarden_core.nodes.data import MarketDataNode, SQLiteNode, PostgresNode
from programgarden_core.nodes.account import AccountNode
from programgarden_core.nodes.symbol import (
    WatchlistNode,
    MarketUniverseNode,
    ScreenerNode,
    SymbolFilterNode,
)
from programgarden_core.nodes.trigger import (
    ScheduleNode,
    TradingHoursFilterNode,
    ExchangeStatusNode,
)
from programgarden_core.nodes.condition import ConditionNode, LogicNode
from programgarden_core.nodes.risk import PositionSizingNode, RiskGuardNode, RiskConditionNode
from programgarden_core.nodes.order import NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode
from programgarden_core.nodes.event import EventHandlerNode, ErrorHandlerNode, AlertNode
from programgarden_core.nodes.display import DisplayNode
from programgarden_core.nodes.group import GroupNode
from programgarden_core.nodes.backtest import (
    HistoricalDataNode,
    BacktestEngineNode,
    PerformanceConditionNode,
)
from programgarden_core.nodes.job import DeployNode, TradingHaltNode, JobControlNode
from programgarden_core.nodes.calculation import CustomPnLNode

__all__ = [
    # Base
    "BaseNode",
    "NodeCategory",
    "Position",
    # Infra
    "StartNode",
    "BrokerNode",
    # Realtime
    "RealMarketDataNode",
    "RealAccountNode",
    "RealOrderEventNode",
    # Data
    "MarketDataNode",
    "AccountNode",
    "HistoricalDataNode",
    "SQLiteNode",
    "PostgresNode",
    # Symbol
    "WatchlistNode",
    "MarketUniverseNode",
    "ScreenerNode",
    "SymbolFilterNode",
    # Trigger
    "ScheduleNode",
    "TradingHoursFilterNode",
    "ExchangeStatusNode",
    # Condition
    "ConditionNode",
    "LogicNode",
    "PerformanceConditionNode",
    # Risk
    "PositionSizingNode",
    "RiskGuardNode",
    "RiskConditionNode",
    # Order
    "NewOrderNode",
    "ModifyOrderNode",
    "CancelOrderNode",
    "LiquidateNode",
    # Event
    "EventHandlerNode",
    "ErrorHandlerNode",
    "AlertNode",
    # Display
    "DisplayNode",
    # Group
    "GroupNode",
    # Backtest
    "BacktestEngineNode",
    # Job
    "DeployNode",
    "TradingHaltNode",
    "JobControlNode",
    # Calculation
    "CustomPnLNode",
]

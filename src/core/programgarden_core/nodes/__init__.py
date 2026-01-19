"""
ProgramGarden Core - 노드 타입 정의

38개 노드 타입을 15개 카테고리로 분류:
- infra (2): StartNode, BrokerNode
- realtime (3): RealMarketDataNode, RealAccountNode, RealOrderEventNode
- data (6): MarketDataNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
- account (1): AccountNode
- symbol (5): WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode
- trigger (3): ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode
- condition (2): ConditionNode, LogicNode
- risk (4): PositionSizingNode, RiskGuardNode, RiskConditionNode, PortfolioNode
- order (3): NewOrderNode, ModifyOrderNode, CancelOrderNode
- event (3): EventHandlerNode, ErrorHandlerNode, AlertNode
- display (1): DisplayNode
- backtest (1): BacktestEngineNode
- job (3): DeployNode, TradingHaltNode, JobControlNode
- calculation (1): PnLCalculatorNode
"""

from programgarden_core.nodes.base import BaseNode, NodeCategory, Position
from programgarden_core.nodes.infra import StartNode, BrokerNode, ThrottleNode
from programgarden_core.nodes.realtime import (
    RealMarketDataNode,
    RealAccountNode,
    RealOrderEventNode,
)
from programgarden_core.nodes.data import MarketDataNode, SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
from programgarden_core.nodes.account import AccountNode
from programgarden_core.nodes.symbol import (
    WatchlistNode,
    MarketUniverseNode,
    ScreenerNode,
    SymbolFilterNode,
    SymbolQueryNode,
)
from programgarden_core.nodes.trigger import (
    ScheduleNode,
    TradingHoursFilterNode,
    ExchangeStatusNode,
)
from programgarden_core.nodes.condition import ConditionNode, LogicNode
from programgarden_core.nodes.risk import PositionSizingNode, RiskGuardNode, RiskConditionNode
from programgarden_core.nodes.order import NewOrderNode, ModifyOrderNode, CancelOrderNode
# event 노드는 커뮤니티 노드(TelegramNode 등)로 대체됨
from programgarden_core.nodes.display import DisplayNode
from programgarden_core.nodes.backtest import (
    HistoricalDataNode,
    BacktestEngineNode,
    BenchmarkCompareNode,
)
from programgarden_core.nodes.portfolio import PortfolioNode
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
    "ThrottleNode",
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
    "HTTPRequestNode",
    "FieldMappingNode",
    # Symbol
    "WatchlistNode",
    "MarketUniverseNode",
    "ScreenerNode",
    "SymbolFilterNode",
    "SymbolQueryNode",
    # Trigger
    "ScheduleNode",
    "TradingHoursFilterNode",
    "ExchangeStatusNode",
    # Condition
    "ConditionNode",
    "LogicNode",
    # Risk
    "PositionSizingNode",
    "RiskGuardNode",
    "RiskConditionNode",
    "PortfolioNode",
    # Order
    "NewOrderNode",
    "ModifyOrderNode",
    "CancelOrderNode",
    # Event - 커뮤니티 노드(TelegramNode 등)로 대체됨
    # Display
    "DisplayNode",
    # Backtest/Analysis
    "BacktestEngineNode",
    "BenchmarkCompareNode",
    # Job
    "DeployNode",
    "TradingHaltNode",
    "JobControlNode",
    # Calculation
    "CustomPnLNode",
]

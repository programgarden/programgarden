"""
ProgramGarden Core - 노드 타입 정의

31개 노드 타입을 10개 카테고리로 분류:
- infra (3): StartNode, BrokerNode, ThrottleNode
- realtime (3): RealMarketDataNode, RealAccountNode, RealOrderEventNode
- data (6): MarketDataNode, HistoricalDataNode, SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
- account (1): AccountNode
- symbol (5): WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode
- trigger (2): ScheduleNode, TradingHoursFilterNode
- condition (2): ConditionNode, LogicNode
- risk (2): PositionSizingNode, PortfolioNode
- order (3): NewOrderNode, ModifyOrderNode, CancelOrderNode
- display (1): DisplayNode
- backtest (2): BacktestEngineNode, BenchmarkCompareNode
- messaging: 커뮤니티 노드 (TelegramNode 등)
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
)
from programgarden_core.nodes.condition import ConditionNode, LogicNode
from programgarden_core.nodes.risk import PositionSizingNode
from programgarden_core.nodes.order import NewOrderNode, ModifyOrderNode, CancelOrderNode
# messaging 노드는 커뮤니티 패키지(TelegramNode 등)에서 제공
from programgarden_core.nodes.display import DisplayNode
from programgarden_core.nodes.backtest import (
    HistoricalDataNode,
    BacktestEngineNode,
    BenchmarkCompareNode,
)
from programgarden_core.nodes.portfolio import PortfolioNode

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
    # Condition
    "ConditionNode",
    "LogicNode",
    # Risk
    "PositionSizingNode",
    "PortfolioNode",
    # Order
    "NewOrderNode",
    "ModifyOrderNode",
    "CancelOrderNode",
    # messaging - 커뮤니티 노드(TelegramNode 등)에서 제공
    # Display
    "DisplayNode",
    # Backtest/Analysis
    "BacktestEngineNode",
    "BenchmarkCompareNode",
]

"""
ProgramGarden Core - 노드 타입 정의

40개 노드 타입을 카테고리로 분류:
- infra (2): StartNode, ThrottleNode
- broker (2): StockBrokerNode, FuturesBrokerNode
- market (12): StockMarketDataNode, FuturesMarketDataNode, StockHistoricalDataNode, FuturesHistoricalDataNode,
              StockRealMarketDataNode, FuturesRealMarketDataNode, StockSymbolQueryNode, FuturesSymbolQueryNode,
              WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode
- account (6): StockAccountNode, FuturesAccountNode, StockRealAccountNode, FuturesRealAccountNode,
              StockRealOrderEventNode, FuturesRealOrderEventNode
- trigger (2): ScheduleNode, TradingHoursFilterNode
- condition (2): ConditionNode, LogicNode
- risk (2): PositionSizingNode, PortfolioNode
- order (6): StockNewOrderNode, StockModifyOrderNode, StockCancelOrderNode,
             FuturesNewOrderNode, FuturesModifyOrderNode, FuturesCancelOrderNode
- display (1): DisplayNode
- backtest (2): BacktestEngineNode, BenchmarkCompareNode
- data (4): SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
- messaging: 커뮤니티 노드 (TelegramNode 등)
"""

from programgarden_core.nodes.base import BaseNode, NodeCategory, Position
from programgarden_core.nodes.infra import StartNode, ThrottleNode
from programgarden_core.nodes.broker import StockBrokerNode, FuturesBrokerNode
# Market - 상품별 분리 노드
from programgarden_core.nodes.data_stock import StockMarketDataNode
from programgarden_core.nodes.data_futures import FuturesMarketDataNode
from programgarden_core.nodes.backtest_stock import StockHistoricalDataNode
from programgarden_core.nodes.backtest_futures import FuturesHistoricalDataNode
from programgarden_core.nodes.realtime_stock import (
    StockRealMarketDataNode,
    StockRealAccountNode,
    StockRealOrderEventNode,
)
from programgarden_core.nodes.realtime_futures import (
    FuturesRealMarketDataNode,
    FuturesRealAccountNode,
    FuturesRealOrderEventNode,
)
from programgarden_core.nodes.account_stock import StockAccountNode
from programgarden_core.nodes.account_futures import FuturesAccountNode
from programgarden_core.nodes.symbol_stock import StockSymbolQueryNode
from programgarden_core.nodes.symbol_futures import FuturesSymbolQueryNode
# Data (상품 무관)
from programgarden_core.nodes.data import SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
# Symbol (상품 무관)
from programgarden_core.nodes.symbol import (
    WatchlistNode,
    MarketUniverseNode,
    ScreenerNode,
    SymbolFilterNode,
)
from programgarden_core.nodes.trigger import (
    ScheduleNode,
    TradingHoursFilterNode,
)
from programgarden_core.nodes.condition import ConditionNode, LogicNode
from programgarden_core.nodes.risk import PositionSizingNode
from programgarden_core.nodes.order import (
    StockNewOrderNode,
    StockModifyOrderNode,
    StockCancelOrderNode,
    FuturesNewOrderNode,
    FuturesModifyOrderNode,
    FuturesCancelOrderNode,
)
# messaging 노드는 커뮤니티 패키지(TelegramNode 등)에서 제공
from programgarden_core.nodes.display import DisplayNode
from programgarden_core.nodes.backtest import (
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
    "ThrottleNode",
    # Broker (상품별 분리)
    "StockBrokerNode",
    "FuturesBrokerNode",
    # Market - Stock (해외주식)
    "StockMarketDataNode",
    "StockHistoricalDataNode",
    "StockRealMarketDataNode",
    "StockSymbolQueryNode",
    # Market - Futures (해외선물)
    "FuturesMarketDataNode",
    "FuturesHistoricalDataNode",
    "FuturesRealMarketDataNode",
    "FuturesSymbolQueryNode",
    # Account - Stock (해외주식)
    "StockAccountNode",
    "StockRealAccountNode",
    "StockRealOrderEventNode",
    # Account - Futures (해외선물)
    "FuturesAccountNode",
    "FuturesRealAccountNode",
    "FuturesRealOrderEventNode",
    # Data (상품 무관)
    "SQLiteNode",
    "PostgresNode",
    "HTTPRequestNode",
    "FieldMappingNode",
    # Symbol (상품 무관)
    "WatchlistNode",
    "MarketUniverseNode",
    "ScreenerNode",
    "SymbolFilterNode",
    # Trigger
    "ScheduleNode",
    "TradingHoursFilterNode",
    # Condition
    "ConditionNode",
    "LogicNode",
    # Risk
    "PositionSizingNode",
    "PortfolioNode",
    # Order (해외주식)
    "StockNewOrderNode",
    "StockModifyOrderNode",
    "StockCancelOrderNode",
    # Order (해외선물)
    "FuturesNewOrderNode",
    "FuturesModifyOrderNode",
    "FuturesCancelOrderNode",
    # messaging - 커뮤니티 노드(TelegramNode 등)에서 제공
    # Display
    "DisplayNode",
    # Backtest/Analysis
    "BacktestEngineNode",
    "BenchmarkCompareNode",
]

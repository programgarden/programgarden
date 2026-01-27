"""
ProgramGarden Core - 노드 타입 정의

40개 노드 타입을 카테고리로 분류:
- infra (2): StartNode, ThrottleNode
- broker (2): OverseasStockBrokerNode, OverseasFuturesBrokerNode
- market (12): OverseasStockMarketDataNode, OverseasFuturesMarketDataNode, OverseasStockHistoricalDataNode, OverseasFuturesHistoricalDataNode,
              OverseasStockRealMarketDataNode, OverseasFuturesRealMarketDataNode, OverseasStockSymbolQueryNode, OverseasFuturesSymbolQueryNode,
              WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode
- account (6): OverseasStockAccountNode, OverseasFuturesAccountNode, OverseasStockRealAccountNode, OverseasFuturesRealAccountNode,
              OverseasStockRealOrderEventNode, OverseasFuturesRealOrderEventNode
- trigger (2): ScheduleNode, TradingHoursFilterNode
- condition (2): ConditionNode, LogicNode
- risk (2): PositionSizingNode, PortfolioNode
- order (6): OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode,
             OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode
- display (1): DisplayNode
- backtest (2): BacktestEngineNode, BenchmarkCompareNode
- data (4): SQLiteNode, PostgresNode, HTTPRequestNode, FieldMappingNode
- messaging: 커뮤니티 노드 (TelegramNode 등)
"""

from programgarden_core.nodes.base import BaseNode, NodeCategory, Position
from programgarden_core.nodes.infra import StartNode, ThrottleNode
from programgarden_core.nodes.broker import OverseasStockBrokerNode, OverseasFuturesBrokerNode
# Market - 상품별 분리 노드
from programgarden_core.nodes.data_stock import OverseasStockMarketDataNode
from programgarden_core.nodes.data_futures import OverseasFuturesMarketDataNode
from programgarden_core.nodes.backtest_stock import OverseasStockHistoricalDataNode
from programgarden_core.nodes.backtest_futures import OverseasFuturesHistoricalDataNode
from programgarden_core.nodes.realtime_stock import (
    OverseasStockRealMarketDataNode,
    OverseasStockRealAccountNode,
    OverseasStockRealOrderEventNode,
)
from programgarden_core.nodes.realtime_futures import (
    OverseasFuturesRealMarketDataNode,
    OverseasFuturesRealAccountNode,
    OverseasFuturesRealOrderEventNode,
)
from programgarden_core.nodes.account_stock import OverseasStockAccountNode
from programgarden_core.nodes.account_futures import OverseasFuturesAccountNode
from programgarden_core.nodes.symbol_stock import OverseasStockSymbolQueryNode
from programgarden_core.nodes.symbol_futures import OverseasFuturesSymbolQueryNode
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
    OverseasStockNewOrderNode,
    OverseasStockModifyOrderNode,
    OverseasStockCancelOrderNode,
    OverseasFuturesNewOrderNode,
    OverseasFuturesModifyOrderNode,
    OverseasFuturesCancelOrderNode,
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
    "OverseasStockBrokerNode",
    "OverseasFuturesBrokerNode",
    # Market - Stock (해외주식)
    "OverseasStockMarketDataNode",
    "OverseasStockHistoricalDataNode",
    "OverseasStockRealMarketDataNode",
    "OverseasStockSymbolQueryNode",
    # Market - Futures (해외선물)
    "OverseasFuturesMarketDataNode",
    "OverseasFuturesHistoricalDataNode",
    "OverseasFuturesRealMarketDataNode",
    "OverseasFuturesSymbolQueryNode",
    # Account - Stock (해외주식)
    "OverseasStockAccountNode",
    "OverseasStockRealAccountNode",
    "OverseasStockRealOrderEventNode",
    # Account - Futures (해외선물)
    "OverseasFuturesAccountNode",
    "OverseasFuturesRealAccountNode",
    "OverseasFuturesRealOrderEventNode",
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
    "OverseasStockNewOrderNode",
    "OverseasStockModifyOrderNode",
    "OverseasStockCancelOrderNode",
    # Order (해외선물)
    "OverseasFuturesNewOrderNode",
    "OverseasFuturesModifyOrderNode",
    "OverseasFuturesCancelOrderNode",
    # messaging - 커뮤니티 노드(TelegramNode 등)에서 제공
    # Display
    "DisplayNode",
    # Backtest/Analysis
    "BacktestEngineNode",
    "BenchmarkCompareNode",
]
